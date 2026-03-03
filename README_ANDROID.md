# Cards Against The Chef - Android Build Instructions

## Voraussetzungen

1. **Python 3.7+** mit virtuellem Environment
2. **Java Development Kit (JDK)** - Version 11 oder höher
3. **Android SDK** - Android Studio oder standalone SDK
4. **Android NDK** - Version 25b (empfohlen)

## Installation

### 1. Virtuelles Environment aktivieren
```bash
cd "c:\Users\Anwender\Desktop\cards against the chef\catc_code"
.venv\Scripts\activate
```

### 2. Buildozer installieren
```bash
pip install buildozer
```

### 3. Umgebungsvariablen setzen (Windows)
Setze diese Umgebungsvariablen in Windows:
- `ANDROID_SDK_ROOT`: Pfad zum Android SDK
- `ANDROID_NDK_ROOT`: Pfad zum Android NDK
- `JAVA_HOME`: Pfad zum JDK

Beispiel:
```
ANDROID_SDK_ROOT=C:\Users\DeinName\AppData\Local\Android\Sdk
ANDROID_NDK_ROOT=C:\Users\DeinName\AppData\Local\Android\Sdk\ndk\25.1.8937393
JAVA_HOME=C:\Program Files\Java\jdk-11.0.12
```

## APK bauen

### 1. Debug-Version (schnell zum Testen)
```bash
buildozer android debug
```

### 2. Release-Version (zum Verteilen)
```bash
buildozer android release
```

Der Build-Prozess kann beim ersten Mal 30-60 Minuten dauern, da alle Abhängigkeiten heruntergeladen werden müssen.

## APK installieren

### Auf Android-Gerät:
1. Gehe zu Einstellungen → Sicherheit → "Unbekannte Quellen" aktivieren
2. Übertrage die APK-Datei (`bin/catc-0.1-debug.apk`) `bin/catc-0.1-release.apk`) auf dein Handy
3. Installiere die APK

### Mit ADB (wenn Developer Mode aktiv):
```bash
adb install bin/catc-0.1-debug.apk
```

## Wichtige Hinweise

- Die App benötigt **Speicherberechtigungen** für die Bilder
- Das Icon wird automatisch von `picsnlists/chefhead.ico` verwendet
- Die App ist im **Portrait-Modus** optimiert
- Unterstützt Android 5.0+ (API Level 21)

## Fehlersuche

### Häufige Probleme:
1. **"NDK not found"**: Überprüfe `ANDROID_NDK_ROOT` Umgebungsvariable
2. **"SDK not found"**: Überprüfe `ANDROID_SDK_ROOT` Umgebungsvariable
3. **"Java not found"**: Überprüfe `JAVA_HOME` Umgebungsvariable
4. **Build schlägt fehl**: Lösche `.buildozer` Ordner und versuche es erneut

### Log-Dateien prüfen:
```bash
buildozer android debug run --log-level=DEBUG
```

## App-Features auf Android

- ✅ Touch-Steuerung optimiert
- ✅ Portrait-Modus
- ✅ Alle Spielmodi funktionieren
- ✅ Previous Decisions Display
- ✅ Custom Icon
- ✅ Speicherberechtigungen

## Dateigröße

Die APK wird ca. 50-80 MB groß sein, da sie die komplette Python-Laufzeitumgebung enthält.
