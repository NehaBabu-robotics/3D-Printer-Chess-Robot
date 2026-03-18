# How to run the project

## On linux

### mjpg streamer

In a terminal, run the following command to start the mjpg streamer:

```
mjpg_streamer -i "input_uvc.so -d /dev/video2 -r 1280x720 -f 15" -o "output_http.so -p 8080 -w /usr/local/share/mjpg-streamer/www"
```

Change the device path, resolution, and frame rate as needed.

The device path can be found using the `ls /dev/video*` command. Try to find the one that corresponds to your camera.

To verify that the mjpg streamer is running, open a web browser and navigate to `http://localhost:8080/?action=stream`. You should see the video stream from your camera.

### Run OctoPrint

In another terminal, navigate to the OctoPrint directory and run the following command to start OctoPrint:

```
cd ~/OctoPrint
python3 -m venv venv
source venv/bin/activate
octoprint serve
```

This will start the OctoPrint server. You can access it by opening a web browser and navigating to `http://localhost:5000`. You should see the OctoPrint interface.

### Connect the printer

Connect the printer to your computer using a micro USB cable. In the OctoPrint interface, go to the "Connection" tab and select the appropriate serial port (e.g., `/dev/ttyUSB0`) and baud rate (115200). Click "Connect" to establish a connection with the printer.

