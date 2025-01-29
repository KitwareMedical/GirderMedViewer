# GirderMedViewer

## Create environment and install dependencies
```
python -m venv env
source env/bin/activate
pip install -e ".[dev]"
```

## Set configuration
Create app.cfg file from the [app.template.cfg](./app.template.cfg), which contains the Girder configuration and custom ui.

## Run trame application
```
girdermedviewer
```
You can add ```--server``` to your command line to prevent your browser from opening and ```--port``` to specifiy the port the server should listen to, default is 8080.
