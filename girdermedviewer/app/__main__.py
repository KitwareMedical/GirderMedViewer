from girdermedviewer.app.core import MedViewerApp


def main(server=None, **kwargs):
    app = MedViewerApp(server)
    app.server.start(**kwargs)


if __name__ == "__main__":
    main()
