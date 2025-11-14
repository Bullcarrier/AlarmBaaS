# Audio File Setup (No Cognitive Services Required)

The function now supports playing a pre-recorded audio file instead of using Cognitive Services.

## Step 1: Create/Record the Audio File

Record or create a WAV file with your message:
**"Hi Operator, this is the Bawat Container. There is a Safety Alarm. Please attend."**

### Audio File Requirements:
- **Format**: WAV
- **Channels**: Mono (single channel)
- **Sample Rate**: 16 kHz
- **Bit Depth**: 16-bit

### Options to Create the File:

1. **Record it yourself**:
   - Use Windows Voice Recorder or any audio recording software
   - Export as WAV, mono, 16 kHz

2. **Use online TTS** (free):
   - Visit: https://ttsmaker.com/ or similar
   - Enter the text: "Hi Operator, this is the Bawat Container. There is a Safety Alarm. Please attend."
   - Download as WAV format

3. **Use Azure Blob Storage + TTS** (if you want):
   - Generate the audio using any TTS service
   - Upload to Azure Blob Storage

## Step 2: Host the Audio File

You need a **publicly accessible URL** to the WAV file. Options:

### Option A: Azure Blob Storage (Recommended)
1. Create a Storage Account in Azure (or use existing)
2. Create a container (set to "Blob" public access)
3. Upload your WAV file
4. Get the blob URL (should look like):
   ```
   https://yourstorageaccount.blob.core.windows.net/container/alarm-message.wav
   ```

### Option B: GitHub (Free)
1. Create a repository (or use existing)
2. Upload the WAV file
3. Use the raw file URL:
   ```
   https://raw.githubusercontent.com/username/repo/main/alarm-message.wav
   ```

### Option C: Any Public URL
- Any web server that can serve the file publicly
- Make sure it's accessible without authentication

## Step 3: Configure Azure Function App

1. Go to Azure Portal → **BaasCall** Function App
2. **Configuration** → **Application settings**
3. Add new setting:
   - **Name**: `AUDIO_FILE_URL`
   - **Value**: Your public URL (e.g., `https://yourstorageaccount.blob.core.windows.net/container/alarm-message.wav`)
4. Click **Save**
5. Restart the Function App (Overview → Restart)

## Step 4: Test

1. Trigger an alarm (or wait for a real one)
2. When the call is answered, the audio file should play automatically

## Troubleshooting

- **No audio plays**: Check that the URL is publicly accessible (try opening it in a browser)
- **File not found**: Verify the URL is correct and the file exists
- **Wrong format**: Ensure the file is WAV, mono, 16 kHz

## Quick Test URL

You can test with a sample audio file first to verify the setup works.

