import { StatusBar } from "expo-status-bar";
import * as Network from "expo-network";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Alert, Modal, PanResponder, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View, useWindowDimensions } from "react-native";
import { useEffect, useRef, useState } from "react";

type SavedComputer = { name: string; ip: string };
type ConnectionState = "desconectado" | "conectando" | "conectado" | "error";
const STORAGE_KEY = "@remote-mouse/computers";

export default function App() {
  const compact = useWindowDimensions().height < 760;
  const [playMode, setPlayMode] = useState<"video" | "youtube" | "system">("video");
  const [host, setHost] = useState("");
  const [name, setName] = useState("");
  const [computers, setComputers] = useState<SavedComputer[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [activeComputer, setActiveComputer] = useState<SavedComputer | null>(null);
  const [state, setState] = useState<ConnectionState>("desconectado");
  const [searching, setSearching] = useState(false);
  const [showAddSheet, setShowAddSheet] = useState(false);
  const socket = useRef<WebSocket | null>(null);
  const lastPosition = useRef<{ x: number; y: number } | null>(null);
  const lastWheelY = useRef(0);
  const ignored = useRef(new Set<string>());

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then((value) => { if (value) setComputers(JSON.parse(value)); })
      .catch(() => undefined)
      .finally(() => setLoaded(true));
  }, []);

  useEffect(() => () => {
    socket.current?.close();
  }, []);

  const rememberComputer = (computer: SavedComputer) => {
    if (ignored.current.has(computer.ip)) return;
    setComputers((current) => {
      const existing = current.find((item) => item.ip === computer.ip);
      const next = [existing ? { ...existing, ...computer } : computer, ...current.filter((item) => item.ip !== computer.ip)];
      AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next)).catch(() => undefined);
      return next;
    });
  };

  const send = (message: object) => {
    if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify(message));
  };

  const deleteComputer = (computer: SavedComputer) => Alert.alert(
    "Eliminar ordenador", `¿Eliminar ${computer.name} de los guardados?`, [
      { text: "Cancelar", style: "cancel" },
      { text: "Eliminar", style: "destructive", onPress: () => {
        ignored.current.add(computer.ip);
        const next = computers.filter((item) => item.ip !== computer.ip);
        setComputers(next);
        void AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next)).catch(() => Alert.alert("Error", "No se pudo guardar la eliminación."));
      } },
    ]);

  const connect = (computer: SavedComputer) => {
    socket.current?.close();
    setState("conectando");
    const ws = new WebSocket(`ws://${computer.ip}:8765`);
    socket.current = ws;
    ws.onopen = () => {
      if (socket.current !== ws) return;
      rememberComputer(computer);
      setActiveComputer(computer);
      setState("conectado");
    };
    ws.onerror = () => { if (socket.current === ws) setState("error"); };
    ws.onclose = () => { if (socket.current === ws) setState("desconectado"); };
  };

  const firstServerIn = (addresses: string[]) => new Promise<string | null>((resolve) => {
    let next = 0;
    let active = 0;
    let settled = false;
    const probes = new Set<WebSocket>();
    const finish = (address: string | null) => {
      if (settled) return;
      settled = true;
      probes.forEach((probe) => probe.close());
      resolve(address);
    };
    const launch = () => {
      while (!settled && active < 32 && next < addresses.length) {
        const address = addresses[next++];
        active += 1;
        const probe = new WebSocket(`ws://${address}:8765`);
        probes.add(probe);
        const timeout = setTimeout(() => {
          probe.close();
          probes.delete(probe);
          active -= 1;
          if (next === addresses.length && active === 0) finish(null); else launch();
        }, 700);
        probe.onopen = () => {
          clearTimeout(timeout);
          probes.delete(probe);
          finish(address);
        };
        probe.onerror = () => {
          clearTimeout(timeout);
          probes.delete(probe);
          active -= 1;
          if (next === addresses.length && active === 0) finish(null); else launch();
        };
      }
    };
    launch();
  });

  const findComputer = async () => {
    if (searching) return;
    setSearching(true);
    try {
      const parts = (await Network.getIpAddressAsync()).split(".");
      if (parts.length !== 4) throw new Error("IPv4 no disponible");
      const base = parts.slice(0, 3).join(".");
      const ownHost = Number(parts[3]);
      const candidates = Array.from({ length: 254 }, (_, index) => index + 1)
        .filter((last) => last !== ownHost)
        .map((last) => `${base}.${last}`);
      const ip = await firstServerIn(candidates);
      if (ip) {
        rememberComputer({ name: "Ordenador encontrado", ip });
        setHost(ip);
        return;
      }
      setState("error");
    } catch { setState("error"); }
    finally { setSearching(false); }
  };

  useEffect(() => { if (loaded) void findComputer(); }, [loaded]);

  const addComputer = () => {
    const ip = host.trim().replace(/^ws:\/\//, "").replace(/:\d+$/, "").replace(/\/$/, "");
    if (!ip) return;
    ignored.current.delete(ip);
    rememberComputer({ name: name.trim() || "Mi ordenador", ip });
    setShowAddSheet(false);
    setName("");
    setHost("");
  };

  const trackpadResponder = useRef(PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onMoveShouldSetPanResponder: () => true,
    onPanResponderGrant: (event) => { lastPosition.current = { x: event.nativeEvent.pageX, y: event.nativeEvent.pageY }; },
    onPanResponderMove: (event) => {
      if (event.nativeEvent.touches.length !== 1) { lastPosition.current = null; return; }
      const current = { x: event.nativeEvent.pageX, y: event.nativeEvent.pageY };
      if (lastPosition.current) send({ type: "move", dx: current.x - lastPosition.current.x, dy: current.y - lastPosition.current.y });
      lastPosition.current = current;
    },
    onPanResponderRelease: (_, gesture) => {
      send({ type: "move_end" });
      if (Math.abs(gesture.dx) < 6 && Math.abs(gesture.dy) < 6) send({ type: "click", button: "left" });
      lastPosition.current = null;
    },
    onPanResponderTerminate: () => { send({ type: "move_end" }); lastPosition.current = null; },
  })).current;

  const wheelResponder = useRef(PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onMoveShouldSetPanResponder: () => true,
    onPanResponderGrant: () => { lastWheelY.current = 0; },
    onPanResponderMove: (_, gesture) => {
      const delta = gesture.dy - lastWheelY.current;
      const steps = Math.trunc(delta / 3);
      if (steps) {
        lastWheelY.current += steps * 3;
        send({ type: "scroll", amount: -steps * 10 });
      }
    },
  })).current;

  const media = (action: string) => send({ type: "media", action });
  const mediaButton = (label: string, action: () => void, extra = {}, accessibilityLabel = label) => <TouchableOpacity accessibilityRole="button" accessibilityLabel={accessibilityLabel} disabled={state !== "conectado"} activeOpacity={.55} style={[styles.mediaButton, extra, state !== "conectado" && { opacity: .4 }]} onPress={action}><Text style={styles.mediaText}>{label}</Text></TouchableOpacity>;

  if (activeComputer) return <View style={[styles.container, compact && { paddingTop: 38, paddingBottom: 12 }]}>
    <StatusBar style="light" />
    <View style={styles.topRow}><TouchableOpacity onPress={() => { socket.current?.close(); setActiveComputer(null); }}><Text style={styles.back}>‹  Ordenadores</Text></TouchableOpacity><Text style={styles.connected}>● {state}</Text></View>
    <Text style={styles.title}>Panel táctil</Text><Text style={styles.subtitle}>{activeComputer.name} · {activeComputer.ip}</Text>
    <View style={[styles.controlRow, { minHeight: compact ? 140 : 200 }]}>
      <View {...trackpadResponder.panHandlers} style={styles.trackpad}><Text style={styles.trackpadIcon}>⌖</Text><Text style={styles.trackpadText}>Desliza para mover{`\n`}Toca para hacer clic</Text></View>
      <View {...wheelResponder.panHandlers} style={styles.wheel}><Text style={styles.wheelGlyph}>↕</Text><Text style={styles.wheelText}>RUEDA</Text></View>
    </View>
    <View style={[styles.remote, compact && { padding: 12, marginTop: 12 }]}>
      <View style={styles.remoteHeader}><View style={styles.remoteLed} /><Text style={styles.remoteTitle}>MEDIA REMOTE</Text><Text style={styles.remoteCaption}>CONTROL</Text></View>
      <View style={styles.modeRow}>{([['video', 'Vídeo'], ['youtube', 'YouTube'], ['system', 'Sistema']] as const).map(([mode, label]) => <TouchableOpacity key={mode} accessibilityRole="button" accessibilityState={{ selected: playMode === mode }} onPress={() => setPlayMode(mode)} style={[styles.mode, playMode === mode && styles.modeSelected]}><Text style={[styles.modeText, playMode === mode && { color: '#b8f5d4' }]}>{label}</Text></TouchableOpacity>)}</View>
      <View style={styles.transport}>
        {mediaButton('⏮', () => media('previous'), styles.roundKey, 'Pista anterior')}
        {mediaButton('▶ Ⅱ', () => media(playMode === 'system' ? 'play_pause' : playMode === 'youtube' ? 'play_pause_youtube' : 'play_pause_video'), [styles.playKey, compact && { width: 66, height: 66, borderRadius: 33 }], 'Reproducir o pausar')}
        {mediaButton('⏭', () => media('next'), styles.roundKey, 'Pista siguiente')}
      </View>
      <View style={styles.seekRow}>{mediaButton('−5', () => media('seek_back'), styles.seekKey, 'Retroceder: flecha izquierda')}<Text style={styles.seekCaption}>VÍDEO</Text>{mediaButton('+5', () => media('seek_forward'), styles.seekKey, 'Adelantar: flecha derecha')}</View>
      <View style={styles.volumeRocker}>{mediaButton('−', () => media('volume_down'), styles.volumeKey, 'Bajar volumen')}<Text style={styles.volumeLabel}>VOLUMEN</Text>{mediaButton('+', () => media('volume_up'), styles.volumeKey, 'Subir volumen')}</View>
      <Text style={styles.remoteHint}>{playMode === 'system' ? 'Control multimedia de Windows' : 'Haz clic en el vídeo antes de usar el mando'}</Text>
    </View>
  </View>;

  return <View style={styles.container}>
    <StatusBar style="light" /><Text style={styles.title}>Ordenadores</Text><Text style={styles.subtitle}>Elige un ordenador para empezar</Text>
    <ScrollView style={styles.computerList} contentContainerStyle={styles.listContent}>
      {computers.map((computer) => <TouchableOpacity key={computer.ip} style={styles.computer} onPress={() => connect(computer)} onLongPress={() => deleteComputer(computer)} delayLongPress={500}><View><Text style={styles.computerName}>{computer.name}</Text><Text style={styles.computerIp}>{computer.ip}</Text></View><Text style={styles.connectText}>Conectar  ›</Text></TouchableOpacity>)}
      {!computers.length && <Text style={styles.hint}>{searching ? "Buscando ordenadores en esta Wi‑Fi…" : "Aún no hay ordenadores guardados."}</Text>}
      <TouchableOpacity style={styles.searchButton} onPress={findComputer} disabled={searching}><Text style={styles.searchText}>{searching ? "Buscando…" : "⌕  Buscar ordenadores en esta Wi‑Fi"}</Text></TouchableOpacity>
      {state === "error" && <Text style={styles.error}>No se encontró ningún ordenador. Puedes añadir su IP manualmente.</Text>}
    </ScrollView>
    <View style={styles.tabs}><Text style={styles.tabActive}>⌂  Ordenadores</Text><Text style={styles.tab}>◎  Panel táctil</Text></View>
    <TouchableOpacity style={styles.fab} onPress={() => setShowAddSheet(true)}><Text style={styles.fabText}>＋</Text></TouchableOpacity>
    <Modal transparent animationType="slide" visible={showAddSheet} onRequestClose={() => setShowAddSheet(false)}><View style={styles.sheetBackdrop}><View style={styles.sheet}><View style={styles.sheetHandle} /><View style={styles.sheetHeader}><Text style={styles.sheetTitle}>Añadir ordenador</Text><TouchableOpacity onPress={() => setShowAddSheet(false)}><Text style={styles.close}>×</Text></TouchableOpacity></View><TextInput value={name} onChangeText={setName} placeholder="Nombre (ej. Mi PC)" placeholderTextColor="#92a0b8" style={styles.input} /><TextInput value={host} onChangeText={setHost} autoCapitalize="none" autoCorrect={false} keyboardType="numeric" placeholder="IP (ej. 192.168.1.25)" placeholderTextColor="#92a0b8" style={styles.input} /><TouchableOpacity style={styles.addButton} onPress={addComputer}><Text style={styles.connectText}>Guardar ordenador</Text></TouchableOpacity></View></View></Modal>
  </View>;
}

const styles = StyleSheet.create({
  remote: { marginTop: 18, padding: 18, borderRadius: 28, backgroundColor: '#202a38', borderWidth: 1, borderColor: '#3e4d60', shadowColor: '#000', shadowOpacity: .35, shadowRadius: 12, shadowOffset: { width: 0, height: 6 }, elevation: 8 },
  remoteHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 }, remoteLed: { width: 6, height: 6, borderRadius: 3, backgroundColor: '#84efb6' }, remoteTitle: { color: '#d8e6f2', fontSize: 10, fontWeight: '800', letterSpacing: 2, flex: 1 }, remoteCaption: { color: '#7c8da5', fontSize: 9, letterSpacing: 1 },
  modeRow: { flexDirection: 'row', backgroundColor: '#111a27', borderRadius: 12, padding: 3 }, mode: { flex: 1, paddingVertical: 8, alignItems: 'center', borderRadius: 9 }, modeSelected: { backgroundColor: '#304b46' }, modeText: { color: '#91a2b8', fontSize: 11, fontWeight: '600' },
  transport: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-evenly', marginVertical: 12 }, roundKey: { flex: 0, width: 50, height: 50, borderRadius: 25, backgroundColor: '#121c2a', borderWidth: 1, borderColor: '#455367' }, playKey: { flex: 0, width: 80, height: 80, borderRadius: 40, backgroundColor: '#337f69', borderWidth: 3, borderColor: '#73c7a7', elevation: 5 },
  seekRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }, seekKey: { flex: 0, width: 72, height: 40, borderRadius: 20, backgroundColor: '#172231', borderWidth: 1, borderColor: '#394b61' }, seekCaption: { color: '#7e91a9', fontSize: 9, letterSpacing: 3 },
  volumeRocker: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#101925', borderRadius: 24, borderWidth: 1, borderColor: '#3b4b60' }, volumeKey: { backgroundColor: 'transparent', height: 42 }, volumeLabel: { color: '#a3b4c8', fontSize: 9, letterSpacing: 2 }, remoteHint: { color: '#8b9eb6', textAlign: 'center', fontSize: 10, marginTop: 10 },
  container: { flex: 1, backgroundColor: "#101828", paddingHorizontal: 22, paddingTop: 60, paddingBottom: 16 }, title: { color: "#fff", fontSize: 30, fontWeight: "700" }, subtitle: { color: "#aebbd1", fontSize: 14, marginTop: 6, marginBottom: 16 }, topRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" }, back: { color: "#84caff", fontSize: 16, fontWeight: "700" }, connected: { color: "#32d583", fontWeight: "700" },
  computerList: { flex: 1 }, listContent: { paddingBottom: 80 }, computer: { backgroundColor: "#1d2939", borderRadius: 13, padding: 16, marginBottom: 9, flexDirection: "row", justifyContent: "space-between", alignItems: "center" }, computerName: { color: "#fff", fontSize: 16, fontWeight: "700" }, computerIp: { color: "#98a2b3", marginTop: 4 }, connectText: { color: "#fff", fontWeight: "700" }, hint: { color: "#98a2b3", marginTop: 15 },
  searchButton: { marginTop: 12, borderRadius: 12, padding: 15, borderWidth: 1, borderColor: "#475467", alignItems: "center" }, searchText: { color: "#84caff", fontWeight: "700" }, error: { color: "#fda29b", marginTop: 10, textAlign: "center" },
  fab: { position: "absolute", right: 24, bottom: 76, width: 60, height: 60, borderRadius: 30, backgroundColor: "#1570ef", justifyContent: "center", alignItems: "center", elevation: 8 }, fabText: { color: "#fff", fontSize: 32, lineHeight: 36, fontWeight: "300" },
  tabs: { flexDirection: "row", justifyContent: "space-around", borderTopWidth: 1, borderTopColor: "#344054", paddingTop: 14 }, tab: { color: "#98a2b3", fontWeight: "600" }, tabActive: { color: "#84caff", fontWeight: "700" },
  sheetBackdrop: { flex: 1, backgroundColor: "rgba(0,0,0,.55)", justifyContent: "flex-end" }, sheet: { backgroundColor: "#182230", borderTopLeftRadius: 26, borderTopRightRadius: 26, padding: 22, paddingBottom: 36 }, sheetHandle: { alignSelf: "center", width: 42, height: 4, borderRadius: 2, backgroundColor: "#667085", marginBottom: 16 }, sheetHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }, sheetTitle: { color: "#fff", fontSize: 20, fontWeight: "700" }, close: { color: "#98a2b3", fontSize: 30 }, input: { height: 50, marginBottom: 11, borderRadius: 10, backgroundColor: "#1d2939", color: "#fff", paddingHorizontal: 14 }, addButton: { alignItems: "center", padding: 16, borderRadius: 12, backgroundColor: "#1570ef" },
  controlRow: { flex: 1, flexDirection: "row", gap: 10, minHeight: 250 }, trackpad: { flex: 1, borderRadius: 20, borderWidth: 1, borderColor: "#475467", backgroundColor: "#182230", alignItems: "center", justifyContent: "center" }, trackpadIcon: { color: "#667085", fontSize: 44, marginBottom: 14 }, trackpadText: { color: "#cbd5e1", textAlign: "center", lineHeight: 22 }, wheel: { width: 52, borderRadius: 18, borderWidth: 1, borderColor: "#475467", backgroundColor: "#1d2939", justifyContent: "space-between", alignItems: "center", paddingVertical: 18 }, wheelGlyph: { color: "#84caff", fontSize: 24 }, wheelText: { color: "#98a2b3", fontSize: 9, fontWeight: "700", transform: [{ rotate: "-90deg" }] },
  mediaPanel: { paddingBottom: 8 }, sectionTitle: { color: "#eaecf0", fontWeight: "700", marginTop: 15, marginBottom: 10 }, mediaRow: { flexDirection: "row", gap: 10, marginBottom: 10 }, mediaButton: { flex: 1, height: 50, borderRadius: 12, backgroundColor: "#344054", alignItems: "center", justifyContent: "center" }, playButton: { backgroundColor: "#1570ef", flex: 1.3 }, mediaText: { color: "#fff", fontWeight: "700" },
});
