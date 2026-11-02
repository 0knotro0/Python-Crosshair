# Python-Crosshair
Overlay trasparente e sempre in primo piano per il mirino nei giochi. Python + tkinter, click-through su Windows.

## Caratteristiche
- Finestra overlay senza bordi, sempre sopra le altre finestre (`-topmost`)
- Sfondo trasparente (color-key): si vede solo il mirino
- **Click-through** su Windows: i clic del mouse passano attraverso l'overlay e arrivano al gioco sottostante
- 6 tipi di mirino: punto, croce, cerchio, croce+cerchio, T, croce con gap centrale
- Colore, dimensione, spessore, gap centrale e opacità regolabili in tempo reale
- Salvataggio/caricamento profilo in `crosshair_overlay_profiles.json` nella tua cartella utente
- Tasto `ESC` per nascondere rapidamente l'overlay

## Requisiti
- Python 3 (tkinter incluso nella maggior parte delle installazioni)
- Click-through nativo: solo Windows (tramite `ctypes`). Su altri sistemi l'overlay funziona ma i clic vengono intercettati.

## Avvio
```bash
python crosshair_overlay.py
```

Poi apri il tuo gioco e posiziona l'overlay con il pulsante **Centra overlay**.

## File
- `crosshair_overlay.py` — applicazione principale
- `crosshair_overlay_profiles.json` — profilo salvato (creato automaticamente)

## Note
Il mirino è disegnato su un canvas tkinter con sfondo reso trasparente. Su Windows si usano le estensioni di finestra `WS_EX_LAYERED` e `WS_EX_TRANSPARENT` per ottenere il click-through.

