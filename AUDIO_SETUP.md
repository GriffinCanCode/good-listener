# Configuring BlackHole for Good Listener

To allow "Good Listener" to hear your system audio (Zoom calls, videos, etc.), you need to route audio through a virtual loopback device like BlackHole.

## 1. Install BlackHole
If you haven't already:
```bash
brew install blackhole-2ch
```
*(You may need to restart your computer after installation)*

## 2. Create a Multi-Output Device
This step is crucial. It allows you to hear the audio while also sending it to BlackHole for the AI.

1.  Open **Audio MIDI Setup** (Cmd+Space, type "Audio MIDI Setup").
2.  Click the **+** icon in the bottom left corner.
3.  Select **Create Multi-Output Device**.
4.  In the list on the right, check **TWO** boxes:
    *   **BlackHole 2ch** (The AI's ear)
    *   **Your Headphones / Speakers** (Your ear)
5.  **Important:** Make sure the "Master Device" is set to your Headphones/Speakers to avoid clock drift issues.
6.  (Optional) Rename this device to something like "AI + Headphones".

## 3. Set System Output
1.  Open **System Settings** -> **Sound**.
2.  Under **Output**, select the **Multi-Output Device** you just created.

## 4. Verify Good Listener
1.  Start the Good Listener backend.
2.  Check the logs. You should see:
    `INFO: Found loopback device: BlackHole 2ch (Index X)`
3.  If it says "Using default input", ensure BlackHole is installed and visible in Audio MIDI Setup.

## Troubleshooting
*   **Can't control volume?** macOS disables volume control for Multi-Output devices. You'll need to adjust volume on the physical device (speaker knob) or use an app like [SoundSource](https://rogueamoeba.com/soundsource/).
*   **Echo/Feedback?** Ensure "Good Listener" is NOT playing the audio back out. The backend is purely listening.

