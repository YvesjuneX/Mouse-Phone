# Publicar Mouse Phone 0.1.0

La v0.1.0 se distribuye solamente desde GitHub Releases: APK para Android y ejecutable para Windows x64.

## APK de Android

1. Desde `mobile-app`, instala EAS CLI e inicia sesión con la cuenta Expo del proyecto:

   ```powershell
   npm install --global eas-cli
   eas login
   ```

2. Genera el APK firmado para distribución interna:

   ```powershell
   eas build --platform android --profile preview
   ```

3. En el primer build, permite que Expo gestione el keystore Android. Descarga el APK desde el enlace que proporciona EAS y pruébalo en un teléfono antes de publicarlo.

## Ejecutable de Windows

Desde la raíz del repositorio ejecuta:

```powershell
.\scripts\build-desktop.ps1 -Version 0.1.0
```

El archivo `MousePhone-0.1.0.exe` se crea en `release-artifacts\desktop`. Prueba el ejecutable en un equipo Windows antes de adjuntarlo a la release.

## GitHub Release

1. Confirma que `master` contiene los cambios y crea la etiqueta `v0.1.0`.
2. Crea una release en GitHub con esa etiqueta.
3. Adjunta el APK y el `.exe`.
4. Incluye las notas de `CHANGELOG.md` y enlaza el código fuente del tag para cumplir GPL-3.0.

> Windows puede mostrar SmartScreen para un ejecutable sin certificado de firma. Es normal en esta primera versión; no desactives controles de seguridad para instalarlo.
