import { StatusBar } from "expo-status-bar";
import * as Network from "expo-network";
import { CameraView, useCameraPermissions } from 'expo-camera';
import { Alert, KeyboardAvoidingView, Modal, PanResponder, Platform, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View, useWindowDimensions } from "react-native";
import { useEffect, useRef, useState } from "react";
import { SafeAreaProvider, initialWindowMetrics, useSafeAreaInsets } from 'react-native-safe-area-context';
import { DISCOVERY_COOLDOWN_MS, discoverComputers, discoveryAddresses } from '../services/network/discovery';
import { loadComputers, saveComputers } from '../services/storage/computers';
import { connectRemoteSocket, sendRemoteMessage } from '../services/websocket/remoteSocket';
import { newKeyPair, SecureSession, sessionCodeSecret } from '../services/websocket/secureSession';
import { deviceId, readCredential, saveCredential } from '../services/storage/deviceIdentity';
import { MediaButton } from '../components/MediaButton';
import type { SavedComputer } from '../features/computers/model';
import { remoteCommands } from '../features/remote-control/commands';

type ConnectionState = "desconectado" | "conectando" | "conectado" | "error";
const RECONNECT_DELAY_MS = 3_000;
const MAX_RECONNECT_ATTEMPTS = 20;

export default function RemoteMouseScreen() {
  return <SafeAreaProvider initialMetrics={initialWindowMetrics}>
    <RemoteMouse />
  </SafeAreaProvider>;
}

function RemoteMouse() {
  const insets = useSafeAreaInsets();
  const window = useWindowDimensions();
  const compact = window.height - insets.top - insets.bottom < 700;
  // Los insets vienen del sistema Android: funcionan con navegación por gestos
  // y con la barra clásica de tres botones, sin asumir su altura.
  const screenInsets = {
    paddingTop: Math.max(12, insets.top + 12),
    paddingBottom: Math.max(16, insets.bottom + 16),
  };
  const sheetInsets = { paddingBottom: Math.max(36, insets.bottom + 20) };
  const scannerInsets = { paddingBottom: Math.max(26, insets.bottom + 16) };
  const [host, setHost] = useState("");
  const [name, setName] = useState("");
  const [computers, setComputers] = useState<SavedComputer[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [activeComputer, setActiveComputer] = useState<SavedComputer | null>(null);
  const [state, setState] = useState<ConnectionState>("desconectado");
  const [searching, setSearching] = useState(false);
  const [searchMessage, setSearchMessage] = useState('');
  const searchRunning = useRef(false);
  const lastDiscoveryAt = useRef(0);
  const [showAddSheet, setShowAddSheet] = useState(false);
  const [showPairingSheet, setShowPairingSheet] = useState(false);
  const [showScanner, setShowScanner] = useState(false);
  const [pairingCode, setPairingCode] = useState('');
  const [codeReady, setCodeReady] = useState(false);
  const [pairingLocked, setPairingLocked] = useState(false);
  const [pairingSubmitting, setPairingSubmitting] = useState(false);
  const [pairingComputer, setPairingComputer] = useState<SavedComputer | null>(null);
  const [pairingError, setPairingError] = useState('');
  const pairingSecret = useRef('');
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const socket = useRef<WebSocket | null>(null);
  const connectedSocket = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempts = useRef(0);
  const manualDisconnect = useRef(false);
  const pairingSubmitInFlight = useRef(false);
  const lastPosition = useRef<{ x: number; y: number } | null>(null);
  const lastWheelY = useRef(0);
  const ignored = useRef(new Set<string>());

  useEffect(() => {
    loadComputers()
      .then(setComputers)
      .catch(() => undefined)
      .finally(() => setLoaded(true));
  }, []);

  useEffect(() => () => {
    manualDisconnect.current = true;
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    socket.current?.close();
  }, []);

  const rememberComputer = (computer: SavedComputer) => {
    setComputers((current) => {
      const existing = current.find((item) => item.ip === computer.ip);
      const next = [existing || computer, ...current.filter((item) => item.ip !== computer.ip)];
      saveComputers(next).catch(() => undefined);
      return next;
    });
  };

  const secureSession = useRef<SecureSession | null>(null);
  const send = (message: object) => {
    if (secureSession.current) sendRemoteMessage(socket.current, secureSession.current.encrypt(message));
  };

  const deleteComputer = (computer: SavedComputer) => Alert.alert(
    "Eliminar ordenador", `¿Eliminar ${computer.name} de los guardados?`, [
      { text: "Cancelar", style: "cancel" },
      { text: "Eliminar", style: "destructive", onPress: () => {
        ignored.current.add(computer.ip);
        const next = computers.filter((item) => item.ip !== computer.ip);
        setComputers(next);
        void saveComputers(next).catch(() => Alert.alert("Error", "No se pudo guardar la eliminación."));
      } },
    ]);

  const stopReconnect = () => {
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    reconnectTimer.current = null;
    reconnectAttempts.current = 0;
  };

  const finishPairingAttempt = () => {
    pairingSubmitInFlight.current = false;
    setPairingSubmitting(false);
  };

  const connect = async (computer: SavedComputer, code: string, forceCode = false, reconnecting = false) => {
    if (!reconnecting) {
      stopReconnect();
      manualDisconnect.current = false;
    }
    const id = await deviceId();
    const credential = !pairingSecret.current && !forceCode ? await readCredential(computer.ip) : null;
    const previousSocket = socket.current;
    socket.current = null;
    previousSocket?.close();
    setState("conectando");
    const ws = connectRemoteSocket(computer.ip);
    (ws as any).reconnecting = reconnecting;
    socket.current = ws;
    ws.onopen = () => { if (socket.current === ws) { const keys = newKeyPair(); const mode = credential ? 'known' : (pairingSecret.current ? 'qr' : 'code'); (ws as any).keys = keys; (ws as any).mode = mode; sendRemoteMessage(ws, { type: 'session_init', mode, public: keys.publicKey, device_id: id, device_name: 'Mi móvil' }); } };
    ws.onmessage = (event) => {
      if (socket.current !== ws) return;
      try {
        const message = JSON.parse(String(event.data));
        if (message.type === 'pair_result' && message.ok === false && message.reason === 'authorization_required') {
          // La autorización temporal ha caducado o fue revocada: ofrecer un emparejamiento nuevo.
          secureSession.current = null;
          pairingSecret.current = '';
          setPairingComputer(computer);
          setPairingCode('');
          setCodeReady(false);
          setPairingLocked(false);
          finishPairingAttempt();
          setPairingError('La autorización temporal de este móvil ha caducado. Introduce un código nuevo o escanea el QR del ordenador.');
          setShowPairingSheet(true);
          setState('desconectado');
          (ws as any).authorizationRejected = true;
          void connect(computer, '', true);
          return;
        }
        if (message.type === 'pair_result' && message.ok === false && message.reason === 'pairing_locked') { secureSession.current = null; setCodeReady(false); setPairingLocked(true); finishPairingAttempt(); setPairingError('El emparejamiento por código está temporalmente bloqueado. Espera unos minutos o escanea el código QR.'); setShowPairingSheet(true); return; }
        if (message.type === 'pair_result' && message.ok === false && message.reason === 'invalid_code') { const remaining = Number.isInteger(message.attempts_remaining) ? message.attempts_remaining : null; secureSession.current = null; setCodeReady(true); finishPairingAttempt(); setPairingError(`El código no es correcto. Corrige los dígitos necesarios e inténtalo de nuevo.${remaining !== null ? ` Te quedan ${remaining} intento${remaining === 1 ? '' : 's'}.` : ''}`); return; }
        if (message.type === 'session_offer') { if ((ws as any).mode === 'code') { (ws as any).offerPublic = message.public; setPairingCode(''); setPairingLocked(false); finishPairingAttempt(); setCodeReady(true); setPairingError('Introduce el código de seis cifras que muestra ahora el ordenador.'); return; } const extra = credential || pairingSecret.current; const session = new SecureSession((ws as any).keys.secretKey, message.public, extra); secureSession.current = session; sendRemoteMessage(ws, session.encrypt({ type: 'confirm', mode: (ws as any).mode })); }
        if (message.type === 'secure') {
          const payload = secureSession.current?.decrypt(message);
          if (payload?.type === 'session_ready') {
            if (payload.credential) void saveCredential(computer.ip, payload.credential).catch(() => setPairingError('No se pudo guardar la autorización de este ordenador.'));
            finishPairingAttempt(); setCodeReady(false); connectedSocket.current = ws; reconnectAttempts.current = 0; rememberComputer(computer); setActiveComputer(computer); setShowPairingSheet(false); setState('conectado');
          }
          if (payload?.type === 'session_ended') {
            manualDisconnect.current = true;
            stopReconnect();
            socket.current = null;
            connectedSocket.current = null;
            secureSession.current = null;
            setState('desconectado');
            setActiveComputer(null);
          }
        }
      } catch { finishPairingAttempt(); setPairingError('La respuesta del ordenador no es válida.'); }
    };
    ws.onerror = () => { if (socket.current === ws && !(ws as any).reconnecting) { finishPairingAttempt(); setPairingError('No se pudo conectar con el ordenador en la red local. Comprueba que ambos dispositivos usan la misma Wi-Fi y que el servidor está iniciado.'); setState("error"); } };
    ws.onclose = (event) => {
      if (socket.current !== ws) return;
      finishPairingAttempt();
      const shouldRetry = (connectedSocket.current === ws || (ws as any).reconnecting)
        && !manualDisconnect.current
        && !(ws as any).authorizationRejected
        && event.code !== 4000
        && event.code !== 4003;
      socket.current = null;
      if (connectedSocket.current === ws) connectedSocket.current = null;
      secureSession.current = null;
      rememberComputer(computer);
      if (shouldRetry) {
        setState('conectando');
        scheduleReconnect(computer);
        return;
      }
      setState("desconectado");
      setActiveComputer(null);
    };
  };

  const scheduleReconnect = (computer: SavedComputer) => {
    if (reconnectTimer.current || manualDisconnect.current) return;
    if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
      setState('error');
      setActiveComputer(null);
      return;
    }
    reconnectTimer.current = setTimeout(async () => {
      reconnectTimer.current = null;
      try {
        const network = await Network.getNetworkStateAsync();
        if (!network.isConnected) { scheduleReconnect(computer); return; }
        if (!await readCredential(computer.ip)) {
          setState('desconectado');
          setActiveComputer(null);
          return;
        }
        reconnectAttempts.current += 1;
        void connect(computer, '', false, true);
      } catch {
        scheduleReconnect(computer);
      }
    }, RECONNECT_DELAY_MS);
  };

  const openPairing = async (computer: SavedComputer) => {
    pairingSecret.current = ''; secureSession.current = null; finishPairingAttempt(); setCodeReady(false); setPairingLocked(false);
    if (await readCredential(computer.ip)) { setPairingComputer(computer); setPairingError(''); void connect(computer, ''); return; }
    setPairingComputer(computer); setPairingCode(''); setPairingError('Preparando un código seguro en el ordenador…'); setShowAddSheet(false); setShowPairingSheet(true); void connect(computer, '', true);
  };

  const submitPairing = () => {
    if (!pairingComputer) return;
    if (pairingSubmitInFlight.current) return;
    if (pairingSecret.current) {
      pairingSubmitInFlight.current = true; setPairingSubmitting(true);
      setPairingError('Conectando mediante el código QR…');
      void connect(pairingComputer, pairingCode.trim());
    } else if (codeReady && socket.current && (socket.current as any).offerPublic) {
      const code = pairingCode.trim();
      if (code.length !== 6) { setPairingError('Introduce los seis dígitos del código que muestra el ordenador.'); return; }
      pairingSubmitInFlight.current = true; setPairingSubmitting(true);
      const session = new SecureSession((socket.current as any).keys.secretKey, (socket.current as any).offerPublic, sessionCodeSecret(code));
      secureSession.current = session;
      sendRemoteMessage(socket.current, session.encrypt({ type: 'confirm', mode: 'code', code })); return;
    } else {
      setPairingError('La conexión segura se está preparando.');
    }
  };

  const openScanner = async () => {
    if (!cameraPermission?.granted) {
      const permission = await requestCameraPermission();
      if (!permission.granted) { setPairingError('Necesitamos permiso para usar la cámara.'); return; }
    }
    setShowScanner(true);
  };

  const handleQr = ({ data }: { data: string }) => {
    try {
      const url = new URL(data);
      const ip = url.searchParams.get('ip'); const code = url.searchParams.get('code'); const secret = url.searchParams.get('secret'); const expires = Number(url.searchParams.get('expires'));
      if (url.protocol !== 'mousephone:' || url.hostname !== 'pair' || !ip || !code || !secret || code.length !== 6 || !Number.isFinite(expires) || expires * 1000 <= Date.now()) throw new Error();
      ignored.current.delete(ip);
      pairingSecret.current = secret; setCodeReady(true); setPairingLocked(false); setShowScanner(false); setPairingComputer({ name: 'Ordenador escaneado', ip }); setPairingCode(code); setPairingError(''); setShowPairingSheet(true);
    } catch { setPairingError('Este código QR no es válido o ya ha caducado.'); }
  };

  const findComputer = async () => {
    if (searchRunning.current) return;
    const now = Date.now();
    if (now - lastDiscoveryAt.current < DISCOVERY_COOLDOWN_MS) {
      const remainingSeconds = Math.ceil((DISCOVERY_COOLDOWN_MS - (now - lastDiscoveryAt.current)) / 1000);
      setSearchMessage(`Espera ${remainingSeconds} s antes de iniciar otra búsqueda.`);
      return;
    }
    lastDiscoveryAt.current = now;
    searchRunning.current = true;
    ignored.current.clear();
    setSearching(true);
    setSearchMessage('Buscando en la red local…');
    try {
      const parts = (await Network.getIpAddressAsync()).split(".");
      if (parts.length !== 4 || parts.some((part) => !/^\d+$/.test(part) || Number(part) > 255) || parts[0] === '0' || parts[0] === '127') throw new Error("No se pudo obtener la IPv4 del móvil. Comprueba la conexión Wi-Fi.");
      const addresses = discoveryAddresses(parts.join('.'), computers.map(computer => computer.ip));
      let visible = 0;
      await discoverComputers(addresses, (computer) => {
        if (ignored.current.has(computer.ip)) return;
        rememberComputer(computer);
        visible++;
        setSearchMessage(`${visible} ordenador(es) encontrado(s). Puedes seleccionarlo mientras continúa la búsqueda.`);
      });
      setSearchMessage(visible ? `${visible} ordenador(es) encontrado(s). Selecciona uno para conectar.` : 'No se encontró ningún ordenador. Comprueba el servidor o añade su IP manualmente.');
    } catch (error) { setSearchMessage(error instanceof Error ? error.message : 'No se pudo completar la búsqueda.'); }
    finally { searchRunning.current = false; setSearching(false); }
  };

  useEffect(() => { if (loaded) void findComputer(); }, [loaded]);

  const addComputer = () => {
    const ip = host.trim().replace(/^ws:\/\//, "").replace(/:\d+$/, "").replace(/\/$/, "");
    if (!ip) return;
    ignored.current.delete(ip);
    void openPairing({ name: name.trim() || "Mi ordenador", ip });
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
      if (lastPosition.current) send(remoteCommands.move(current.x - lastPosition.current.x, current.y - lastPosition.current.y));
      lastPosition.current = current;
    },
    onPanResponderRelease: (_, gesture) => {
      send(remoteCommands.moveEnd());
      if (Math.abs(gesture.dx) < 6 && Math.abs(gesture.dy) < 6) send(remoteCommands.click());
      lastPosition.current = null;
    },
    onPanResponderTerminate: () => { send(remoteCommands.moveEnd()); lastPosition.current = null; },
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
        send(remoteCommands.scroll(-steps * 11));
      }
    },
  })).current;

  const media = (action: string) => send(remoteCommands.media(action));
  const mediaButton = (label: string, action: () => void, extra = {}, accessibilityLabel = label) => <MediaButton label={label} accessibilityLabel={accessibilityLabel} disabled={state !== "conectado"} onPress={action} style={[styles.mediaButton, extra]} textStyle={styles.mediaText} />;

  if (activeComputer) return <ScrollView
    style={styles.safeRoot}
    contentContainerStyle={[styles.container, styles.controlContent, screenInsets]}
    contentInsetAdjustmentBehavior="never"
    keyboardShouldPersistTaps="handled"
  >
    <StatusBar style="light" />
    <View style={styles.topRow}><TouchableOpacity onPress={() => { manualDisconnect.current = true; stopReconnect(); rememberComputer(activeComputer); socket.current?.close(); setActiveComputer(null); }}><Text style={styles.back}>‹  Ordenadores</Text></TouchableOpacity><Text style={[styles.connected, state !== 'conectado' && styles.connecting]}>● {state}</Text></View>
    <Text style={styles.title}>Panel táctil</Text><Text style={styles.subtitle}>{activeComputer.name} · {activeComputer.ip}</Text>
    <View style={[styles.controlRow, { minHeight: compact ? 140 : 200 }]}>
      <View {...trackpadResponder.panHandlers} style={styles.trackpad}><Text style={styles.trackpadIcon}>⌖</Text><Text style={styles.trackpadText}>Desliza para mover{`\n`}Toca para hacer clic</Text></View>
      <View {...wheelResponder.panHandlers} style={styles.wheel}><Text style={styles.wheelGlyph}>↕</Text><Text style={styles.wheelText}>RUEDA</Text></View>
    </View>
    <View style={[styles.remote, compact && { padding: 12, marginTop: 12 }]}>
      <View style={styles.remoteHeader}><View style={styles.remoteLed} /><Text style={styles.remoteTitle}>MEDIA REMOTE</Text><Text style={styles.remoteCaption}>CONTROL</Text></View>
      <View style={styles.transport}>
        {mediaButton('⏮', () => media('previous'), styles.roundKey, 'Pista anterior')}
        {mediaButton('▶ Ⅱ', () => media('play_pause'), [styles.playKey, compact && { width: 66, height: 66, borderRadius: 33 }], 'Reproducir o pausar')}
        {mediaButton('⏭', () => media('next'), styles.roundKey, 'Pista siguiente')}
      </View>
      <View style={styles.seekRow}>{mediaButton('−5', () => media('seek_back'), styles.seekKey, 'Retroceder: flecha izquierda')}<Text style={styles.seekCaption}>VÍDEO</Text>{mediaButton('+5', () => media('seek_forward'), styles.seekKey, 'Adelantar: flecha derecha')}</View>
      <View style={styles.volumeRocker}>{mediaButton('−', () => media('volume_down'), styles.volumeKey, 'Bajar volumen')}<Text style={styles.volumeLabel}>VOLUMEN</Text>{mediaButton('+', () => media('volume_up'), styles.volumeKey, 'Subir volumen')}</View>
    </View>
  </ScrollView>;

  return <View style={[styles.container, screenInsets]}>
    <StatusBar style="light" /><View style={styles.listHeader}><View><Text style={styles.title}>Ordenadores</Text><Text style={styles.subtitle}>Elige un ordenador para empezar</Text></View><TouchableOpacity accessibilityRole="button" accessibilityLabel="Añadir ordenador mediante código QR" style={styles.qrButton} onPress={openScanner}><Text style={styles.qrButtonIcon}>▣</Text><Text style={styles.qrButtonText}>QR</Text></TouchableOpacity></View>
    <ScrollView style={styles.computerList} contentContainerStyle={[styles.listContent, { paddingBottom: Math.max(96, insets.bottom + 86) }]}>
      {computers.map((computer) => <TouchableOpacity key={computer.ip} style={styles.computer} onPress={() => openPairing(computer)} onLongPress={() => deleteComputer(computer)} delayLongPress={500}><View><Text style={styles.computerName}>{computer.name}</Text><Text style={styles.computerIp}>{computer.ip}</Text></View><Text style={styles.connectText}>Conectar  ›</Text></TouchableOpacity>)}
      {!computers.length && <Text style={styles.hint}>{searching ? "Buscando ordenadores en esta Wi‑Fi…" : "Aún no hay ordenadores guardados."}</Text>}
      <TouchableOpacity style={styles.searchButton} onPress={findComputer} disabled={searching}><Text style={styles.searchText}>{searching ? "Buscando…" : "⌕  Buscar ordenadores en esta Wi‑Fi"}</Text></TouchableOpacity>
      {!!searchMessage && <Text style={styles.hint}>{searchMessage}</Text>}
      {state === "error" && <Text style={styles.error}>No se pudo conectar con el ordenador seleccionado.</Text>}
    </ScrollView>
    <TouchableOpacity style={[styles.fab, { bottom: Math.max(24, insets.bottom + 16) }]} onPress={() => setShowAddSheet(true)}><Text style={styles.fabText}>＋</Text></TouchableOpacity>
    <Modal transparent animationType="slide" visible={showAddSheet} onRequestClose={() => setShowAddSheet(false)}><KeyboardAvoidingView style={styles.sheetBackdrop} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}><View style={[styles.sheet, sheetInsets]}><View style={styles.sheetHandle} /><View style={styles.sheetHeader}><Text style={styles.sheetTitle}>Añadir ordenador</Text><TouchableOpacity onPress={() => setShowAddSheet(false)}><Text style={styles.close}>×</Text></TouchableOpacity></View><TextInput value={name} onChangeText={setName} placeholder="Nombre (ej. Mi PC)" placeholderTextColor="#92a0b8" style={styles.input} /><TextInput value={host} onChangeText={setHost} autoCapitalize="none" autoCorrect={false} keyboardType="numeric" placeholder="IP (ej. 192.168.1.25)" placeholderTextColor="#92a0b8" style={styles.input} /><TouchableOpacity style={styles.addButton} onPress={addComputer}><Text style={styles.connectText}>Continuar con código</Text></TouchableOpacity><TouchableOpacity style={styles.qrAlternative} onPress={openScanner}><Text style={styles.searchText}>▣  Escanear código QR</Text></TouchableOpacity></View></KeyboardAvoidingView></Modal>
    <Modal transparent animationType="slide" visible={showPairingSheet} onRequestClose={() => setShowPairingSheet(false)}>
      <KeyboardAvoidingView style={styles.sheetBackdrop} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}><View style={[styles.sheet, sheetInsets]}>
        <View style={styles.sheetHandle} />
        <View style={styles.sheetHeader}><Text style={styles.sheetTitle}>Confirmar ordenador</Text><TouchableOpacity onPress={() => setShowPairingSheet(false)}><Text style={styles.close}>×</Text></TouchableOpacity></View>
        <Text style={styles.pairingInfo}>{pairingComputer?.name} · {pairingComputer?.ip}</Text>
        {pairingSecret.current ? <Text style={styles.pairingHelp}>El QR ya contiene la autorización. Pulsa para conectar de forma segura.</Text> : pairingLocked ? <Text style={styles.pairingHelp}>El emparejamiento por código está temporalmente bloqueado. Puedes usar el QR o volver a intentarlo más tarde.</Text> : codeReady ? <><Text style={styles.pairingHelp}>Introduce el código de seis cifras que muestra ahora el ordenador.</Text><TextInput editable={!pairingSubmitting} value={pairingCode} onChangeText={(value) => setPairingCode(value.replace(/\D/g, '').slice(0, 6))} keyboardType="number-pad" maxLength={6} placeholder="000000" placeholderTextColor="#92a0b8" style={[styles.input, styles.codeInput]} /></> : <Text style={styles.pairingHelp}>Preparando un código nuevo en el ordenador…</Text>}
        <TouchableOpacity disabled={pairingSubmitting || pairingLocked || (!pairingSecret.current && !codeReady)} style={[styles.addButton, (pairingSubmitting || pairingLocked || (!pairingSecret.current && !codeReady)) && styles.disabledButton]} onPress={submitPairing}><Text style={styles.connectText}>{pairingSubmitting ? 'Comprobando código…' : pairingSecret.current ? 'Conectar mediante QR' : pairingLocked ? 'Emparejamiento bloqueado' : codeReady ? 'Conectar de forma segura' : 'Esperando código…'}</Text></TouchableOpacity>
        <TouchableOpacity style={styles.qrAlternative} onPress={openScanner}><Text style={styles.searchText}>▣  Escanear código QR</Text></TouchableOpacity>
        {!!pairingError && <Text style={styles.error}>{pairingError}</Text>}
      </View></KeyboardAvoidingView>
    </Modal>
    <Modal visible={showScanner} animationType="slide" onRequestClose={() => setShowScanner(false)}><View style={styles.scanner}><CameraView style={styles.camera} facing="back" barcodeScannerSettings={{ barcodeTypes: ['qr'] }} onBarcodeScanned={handleQr} /><View style={[styles.scannerOverlay, scannerInsets]}><Text style={styles.scannerTitle}>Escanea el QR del ordenador</Text><Text style={styles.scannerHint}>El código cambia automáticamente por seguridad.</Text><TouchableOpacity style={styles.scannerClose} onPress={() => setShowScanner(false)}><Text style={styles.connectText}>Cancelar</Text></TouchableOpacity></View></View></Modal>
  </View>;
}

const styles = StyleSheet.create({
  safeRoot: { flex: 1, backgroundColor: '#101828' },
  controlContent: { flex: undefined, flexGrow: 1 },
  remote: { marginTop: 18, padding: 18, borderRadius: 28, backgroundColor: '#202a38', borderWidth: 1, borderColor: '#3e4d60', shadowColor: '#000', shadowOpacity: .35, shadowRadius: 12, shadowOffset: { width: 0, height: 6 }, elevation: 8 },
  remoteHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 }, remoteLed: { width: 6, height: 6, borderRadius: 3, backgroundColor: '#84efb6' }, remoteTitle: { color: '#d8e6f2', fontSize: 10, fontWeight: '800', letterSpacing: 2, flex: 1 }, remoteCaption: { color: '#7c8da5', fontSize: 9, letterSpacing: 1 },
  modeRow: { flexDirection: 'row', backgroundColor: '#111a27', borderRadius: 12, padding: 3 }, mode: { flex: 1, paddingVertical: 8, alignItems: 'center', borderRadius: 9 }, modeSelected: { backgroundColor: '#304b46' }, modeText: { color: '#91a2b8', fontSize: 11, fontWeight: '600' },
  transport: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-evenly', marginVertical: 12 }, roundKey: { flex: 0, width: 50, height: 50, borderRadius: 25, backgroundColor: '#121c2a', borderWidth: 1, borderColor: '#455367' }, playKey: { flex: 0, width: 80, height: 80, borderRadius: 40, backgroundColor: '#337f69', borderWidth: 3, borderColor: '#73c7a7', elevation: 5 },
  seekRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }, seekKey: { flex: 0, width: 72, height: 40, borderRadius: 20, backgroundColor: '#172231', borderWidth: 1, borderColor: '#394b61' }, seekCaption: { color: '#7e91a9', fontSize: 9, letterSpacing: 3 },
  volumeRocker: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#101925', borderRadius: 24, borderWidth: 1, borderColor: '#3b4b60' }, volumeKey: { backgroundColor: 'transparent', height: 42 }, volumeLabel: { color: '#a3b4c8', fontSize: 9, letterSpacing: 2 }, remoteHint: { color: '#8b9eb6', textAlign: 'center', fontSize: 10, marginTop: 10 },
  container: { flex: 1, backgroundColor: "#101828", paddingHorizontal: 22, paddingTop: 12, paddingBottom: 16 }, listHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' }, title: { color: "#fff", fontSize: 30, fontWeight: "700" }, subtitle: { color: "#aebbd1", fontSize: 14, marginTop: 6, marginBottom: 16 }, qrButton: { width: 54, height: 54, borderRadius: 14, borderWidth: 1, borderColor: '#4d6480', backgroundColor: '#182a3d', justifyContent: 'center', alignItems: 'center' }, qrButtonIcon: { fontSize: 20, color: '#84caff', lineHeight: 19 }, qrButtonText: { color: '#bcd3ee', fontSize: 9, fontWeight: '800', letterSpacing: 1 }, topRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" }, back: { color: "#84caff", fontSize: 16, fontWeight: "700" }, connected: { color: "#32d583", fontWeight: "700" }, connecting: { color: '#fdb022' },
  computerList: { flex: 1 }, listContent: { paddingBottom: 80 }, computer: { backgroundColor: "#1d2939", borderRadius: 13, padding: 16, marginBottom: 9, flexDirection: "row", justifyContent: "space-between", alignItems: "center" }, computerName: { color: "#fff", fontSize: 16, fontWeight: "700" }, computerIp: { color: "#98a2b3", marginTop: 4 }, connectText: { color: "#fff", fontWeight: "700" }, hint: { color: "#98a2b3", marginTop: 15 },
  searchButton: { marginTop: 12, borderRadius: 12, padding: 15, borderWidth: 1, borderColor: "#475467", alignItems: "center" }, searchText: { color: "#84caff", fontWeight: "700" }, error: { color: "#fda29b", marginTop: 10, textAlign: "center" },
  fab: { position: "absolute", right: 24, bottom: 76, width: 60, height: 60, borderRadius: 30, backgroundColor: "#1570ef", justifyContent: "center", alignItems: "center", elevation: 8 }, fabText: { color: "#fff", fontSize: 32, lineHeight: 36, fontWeight: "300" },
  tabs: { flexDirection: "row", justifyContent: "space-around", borderTopWidth: 1, borderTopColor: "#344054", paddingTop: 14 }, tab: { color: "#98a2b3", fontWeight: "600" }, tabActive: { color: "#84caff", fontWeight: "700" },
  sheetBackdrop: { flex: 1, backgroundColor: "rgba(0,0,0,.55)", justifyContent: "flex-end" }, sheet: { backgroundColor: "#182230", borderTopLeftRadius: 26, borderTopRightRadius: 26, padding: 22, paddingBottom: 36 }, sheetHandle: { alignSelf: "center", width: 42, height: 4, borderRadius: 2, backgroundColor: "#667085", marginBottom: 16 }, sheetHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }, sheetTitle: { color: "#fff", fontSize: 20, fontWeight: "700" }, close: { color: "#98a2b3", fontSize: 30 }, input: { height: 50, marginBottom: 11, borderRadius: 10, backgroundColor: "#1d2939", color: "#fff", paddingHorizontal: 14 }, codeInput: { textAlign: 'center', fontSize: 26, letterSpacing: 8, fontWeight: '700' }, pairingInfo: { color: '#d5e2f1', fontWeight: '700', marginBottom: 6 }, pairingHelp: { color: '#98a2b3', lineHeight: 20, marginBottom: 16 }, qrAlternative: { alignItems: 'center', padding: 14, marginTop: 6 }, addButton: { alignItems: "center", padding: 16, borderRadius: 12, backgroundColor: "#1570ef" }, disabledButton: { backgroundColor: '#475467' }, scanner: { flex: 1, backgroundColor: '#101828' }, camera: { flex: 1 }, scannerOverlay: { position: 'absolute', left: 0, right: 0, bottom: 0, padding: 26, backgroundColor: 'rgba(16,24,40,.94)' }, scannerTitle: { color: '#fff', fontSize: 21, fontWeight: '700' }, scannerHint: { color: '#b4c4d7', marginTop: 6 }, scannerClose: { marginTop: 18, alignItems: 'center', padding: 14, borderRadius: 12, backgroundColor: '#344054' },
  controlRow: { flex: 1, flexDirection: "row", gap: 10, minHeight: 250 }, trackpad: { flex: 1, borderRadius: 20, borderWidth: 1, borderColor: "#475467", backgroundColor: "#182230", alignItems: "center", justifyContent: "center" }, trackpadIcon: { color: "#667085", fontSize: 44, marginBottom: 14 }, trackpadText: { color: "#cbd5e1", textAlign: "center", lineHeight: 22 }, wheel: { width: 52, borderRadius: 18, borderWidth: 1, borderColor: "#475467", backgroundColor: "#1d2939", justifyContent: "space-between", alignItems: "center", paddingVertical: 18 }, wheelGlyph: { color: "#84caff", fontSize: 24 }, wheelText: { color: "#98a2b3", fontSize: 9, fontWeight: "700", transform: [{ rotate: "-90deg" }] },
  mediaPanel: { paddingBottom: 8 }, sectionTitle: { color: "#eaecf0", fontWeight: "700", marginTop: 15, marginBottom: 10 }, mediaRow: { flexDirection: "row", gap: 10, marginBottom: 10 }, mediaButton: { flex: 1, height: 50, borderRadius: 12, backgroundColor: "#344054", alignItems: "center", justifyContent: "center" }, playButton: { backgroundColor: "#1570ef", flex: 1.3 }, mediaText: { color: "#fff", fontWeight: "700" },
});
