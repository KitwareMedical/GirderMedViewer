# GirderMedViewer

## Create environment and install requirements
```
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

## Set configuration
Create app.cfg file from the app.template.cfg, which contains the Girder configuration and custom ui.
```
[girder]
url: URL to Girder
api_root: suffix to Girder API (usually api/v1)

[ui]
name: Application title to display in the toolbar
```

## Run trame application
```
python vtk_viewer.py
```
You can add ```--server``` to your command line to prevent your browser from opening and ```--port``` to specifiy the port the server should listen to, default is 8080.
