# GirderMedViewer

<img width="1575" height="811" alt="vtk_girder_med_viewer" src="https://github.com/user-attachments/assets/62ecb8a5-8812-4208-a2d3-d95c4caf401e" />

## Create environment and install dependencies
```
python -m venv env
source env/bin/activate
pip install -e ".[dev]"
```

## Setup configuration
To configure the application, create an `app.cfg` file based on the provided [app.template.cfg](./app.template.cfg). This configuration file allows you to:

- **UI Settings**: Customize the application title displayed in the toolbar.
- **Logging Configuration**: Define the logging level (e.g., `INFO` or `DEBUG`).
- **File Download Management**: Set up temporary storage for downloaded files.
- **Girder Connection**: Configure the API root and default connection settings.

By default, a standard Girder configuration is expected, but you can specify additional settings for predefined URLs if needed.

## Run trame application
```
girdermedviewer
```
You can add ```--server``` to your command line to prevent your browser from opening and ```--port``` to specifiy the port the server should listen to, default is 8080.

## Deploy Girder plugin to avoid download
You can add the [GirderMedViewer Plugin](./utils/girdermedviewer_plugin) to your Girder to allow the Trame app to access the paths of the Girder files stored in assetstores. Therefore the Girder files do not need to be downloaded and can be read directly from the Girder assetstores whose paths have been specified in the configuration file (`app.cfg`).

Follow the [plugin README](./utils/girdermedviewer_plugin/README.md) to install it.

## Deploy without launcher
```
python -m trame.tools.serve --exec girdermedviewer.app.core:MyTrameApp
```
This is not for production. It creates a unique process for multiple users.

## Deploy with wslink launcher
Create empty file "proxy-mapping.txt" and empty folder "logs".
Update examples/launcher/launcher.json and index.html to fix paths.

Start launcher:
```
python -m wslink.launcher .\examples\launcher\launcher.json --debug
```

Open launcher page at "localhost:9999"
