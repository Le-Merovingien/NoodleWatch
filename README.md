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
3. **Configuration:** copy `printwatch/printwatch.ini.exemple` to `/etc/printwatch.ini`. Fill in the printer's address and the PrusaLink password, shown on the printer's screen: Settings > Network > PrusaLink.
4. **Automatic start:**
   ```bash
   adb push printwatch/printwatch.service /etc/systemd/system/
   adb shell systemctl enable --now printwatch
   ```

For a first try, set `pause = false` (observation mode): alerts are saved without stopping the print.

## To check on the board

These points could not be checked without the hardware:
- **Camera:** the OV5647 should show up as `/dev/video0`. If not, put a GStreamer pipeline in `source`.
- **Python packages:** `numpy`, `opencv` and `torq-runtime` must be present on the board's image, as in the Synaptics demos.
- **Alert:** the command that drives the HAT's buzzer and LEDs is still to be written, because their pins are not documented.

## Model

YOLOv8n at 320 × 320, two classes: spaghetti and blob ("blob of death", class name `boule`). It is trained on the Roboflow datasets "3D printing failure" and "Defect Detection in 3D Printing" (CC BY 4.0, see [CREDITS.md](CREDITS.md)), then converted to int8 and compiled for the SL2610's NPU. The application alerts on either class.

Results on the NPU simulator, at a threshold of 0.18, on 1,565 images the model has never seen (half of "Defect Detection", split by original photo, with no duplicates of the training set):
- **85 %** of spaghetti images are detected by the spaghetti class (61 out of 72), and 88 % trigger an alert;
- **74 %** of blob images are detected by the blob class;
- **12 %** of images with another defect (strings, under-extrusion, clogged nozzle…) are wrongly flagged, image by image. The 3-out-of-5 filter discards isolated cases.

## License and credits

NoodleWatch is released under the GNU Affero General Public License v3.0 (see [LICENSE](LICENSE)), because the model is trained with Ultralytics YOLOv8, which is under AGPL-3.0.

The training datasets come from Roboflow Universe, under CC BY 4.0: see [CREDITS.md](CREDITS.md).
