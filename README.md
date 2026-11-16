# NoodleWatch

Project page and printable box: [NoodleWatch on Printables](https://www.printables.com/model/1887405-noodlewatch-spaghetti-detection-for-prusa-core-one).

The code and its commands still use the project's working name, `printwatch`.

NoodleWatch watches the print bed through the Coralboard camera. During a print, one image every 5 seconds goes through the "spaghetti" model on the board's NPU. When 3 of the last 5 images show spaghetti, NoodleWatch:
- pauses the print through PrusaLink;
- saves the annotated image;
- runs the alert command (buzzer and LEDs of the HAT).

Optionally, the box also works as a Prusa Connect camera: one photo per minute during the print, the alert image, and a final photo to post the make.

## Installation on the board

1. **Network:** fit the M.2 Wi-Fi module (Ampak AP12611_M2, not included) and connect the board to the printer's network.
2. **Copy:** connect the board to the PC over USB-C, then copy the folder:
   ```bash
   adb push printwatch /opt/printwatch
   ```
3. **Python packages:** the Torq runtime that drives the NPU is not on the board's image. Create a virtual environment that keeps the image's own packages (its OpenCV is built with GStreamer, which the camera needs), then install the requirements. The board must be on the network:
   ```bash
   adb shell python3 -m venv /opt/printwatch-venv --system-site-packages
   adb shell /opt/printwatch-venv/bin/pip install -r /opt/printwatch/requirements.txt
   ```
4. **Configuration:** the file must be edited before it goes on the board. On the PC, copy `printwatch/printwatch.ini.exemple` to `printwatch.ini` and fill in the printer's address (`hote`) and the PrusaLink password (`mot_de_passe`), shown on the printer's screen: Settings > Network > PrusaLink. Then copy it to the board:
   ```bash
   adb push printwatch.ini /etc/printwatch.ini
   ```
5. **Automatic start:**
   ```bash
   adb push printwatch/printwatch.service /etc/systemd/system/
   adb shell systemctl enable --now printwatch
   ```

For a first try, set `pause = false` (observation mode): alerts are saved without stopping the print.

## Prusa Buddy3D camera

NoodleWatch can also use the Buddy3D camera inside the CORE One instead of the box camera:
1. In the Prusa app, enable RTSP for the camera. The stream is then available on the local network only, unencrypted.
2. In `printwatch.ini`, set `source = rtsp://<camera IP>/live`.

The stream is read continuously in the background, so each analysis uses the latest image, and NoodleWatch reconnects on its own if the stream drops. With the Buddy3D, nothing needs to be mounted on the door: the program can run on the board anywhere on the network, or on a Linux PC with `materiel = tflite` (Python packages `numpy`, `opencv-python` and `ai-edge-litert`), with `python -m printwatch printwatch.ini`.

Not yet tested with a real Buddy3D camera.

## To check on the board

These points could not be checked without the hardware:
- **Camera:** the OV5647 should show up as `/dev/video0`. If not, put a GStreamer pipeline in `source`.
- **Board image:** Synaptics tested its SL2610 examples with Torq 2.3 on the scarthgap 6.12 v2.5.0 (Coralboard I/O Edition) and v2.6.1 images. The model is compiled with Torq 2.3.0.
- **Alert:** the command that drives the HAT's buzzer and LEDs is still to be written, because their pins are not documented.
- **Buddy3D:** decoding the HD stream continuously uses some CPU on the board; not measured yet.

## Model

YOLOv8n at 320 × 320, two classes: spaghetti and blob ("blob of death", class name `boule`). It is trained on the Roboflow datasets "3D printing failure" and "Defect Detection in 3D Printing" (CC BY 4.0, see [CREDITS.md](CREDITS.md)), then converted to int8 and compiled for the SL2610's NPU. The application alerts on either class.

Results on the NPU simulator, at a threshold of 0.18, on 1,565 images the model has never seen (half of "Defect Detection", split by original photo, with no duplicates of the training set):
- **85 %** of spaghetti images are detected by the spaghetti class (61 out of 72), and 88 % trigger an alert;
- **74 %** of blob images are detected by the blob class;
- **12 %** of images with another defect (strings, under-extrusion, clogged nozzle…) are wrongly flagged, image by image. The 3-out-of-5 filter discards isolated cases.

## License and credits

NoodleWatch is released under the GNU Affero General Public License v3.0 (see [LICENSE](LICENSE)), because the model is trained with Ultralytics YOLOv8, which is under AGPL-3.0.

The training datasets come from Roboflow Universe, under CC BY 4.0: see [CREDITS.md](CREDITS.md).
