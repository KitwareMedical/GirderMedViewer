from trame.app import get_server
from trame.ui.vuetify import SinglePageWithDrawerLayout, SinglePageLayout
from trame.widgets import gwc, html
from trame.widgets import vuetify2 as vuetify
from girder_client import GirderClient
import os
import shutil

# -----------------------------------------------------------------------------
# Trame setup
# -----------------------------------------------------------------------------

server = get_server(client_type = "vue2")
state, ctrl = server.state, server.controller
state.update({
    "api_url": "https://mille-feuilles.ihu-liryc.fr/api/v1",
    "display_authentication": False,
    "main_drawer": False, #default False, when not connected. If connected and no file selected True
    "path": os.environ.get("TRAME_APP_API_URL", "https://mille-feuilles.ihu-liryc.fr/"),
    "selected": [],
    "select_index": 0,
    "user": None,
})

CLIENT = None


# -----------------------------------------------------------------------------
# API connection
# -----------------------------------------------------------------------------

def disconnect():
    state.api_url = None
    state.path = None
    state.user = None
    state.token = None

def connect():
    state.api_url = state.path + "/api/v1"


# -----------------------------------------------------------------------------
# Data management
# -----------------------------------------------------------------------------

@state.change("api_url")
def set_client(api_url, **kwargs):
    if api_url:
        CLIENT = GirderClient(apiUrl=api_url)
    else:
        CLIENT = None


@state.change("user")
def set_user(user, **kwargs):
    if user:
        state.firstName = user.get("firstName", "").capitalize()
        state.lastName = user.get("lastName", "").upper()
        state.location = user
        CLIENT.setToken(state.token)
    else:
        #TODO check dirty state
        state.firstName = None
        state.lastName = None
        state.location = None
        CLIENT.token = None
        state.main_drawer = False


# @state.change("location", "selected")
# def set_data_details(**kwargs):
#     if state.selected:
#         state.data_details = state.selected
#     elif state.location and state.location.get("_id", ""):
#         state.data_details = [state.location]
#     else:
#         state.data_details = []


def update_location(new_location):
    state.location = new_location


def handle_rowclick(row):
    if row.get('_modelType') == 'item':
        if len(state.selected) < 4:
            state.selected.append(row)
        else:
            item_to_delete = state.selected[state.select_index]
            shutil.rmtree(os.path.join("filestore", item_to_delete["name"]))
            state.selected[state.select_index] = row
            state.select_index += 1
        
        print([s["name"] for s in state.selected])
        CLIENT.downloadItem(
            row["_id"],
            os.path.join("filestore", row["name"]),
            row["name"]
        )


# -----------------------------------------------------------------------------
# Girder provider initialization
# -----------------------------------------------------------------------------

provider = gwc.GirderProvider(value=("api_url",), trame_server=server)
ctrl.provider_logout = provider.logout


# -----------------------------------------------------------------------------
# Layout
# -----------------------------------------------------------------------------

with SinglePageWithDrawerLayout(server, show_drawer=False, width="25%") as layout:
    provider.register_layout(layout)
    # TODO redo bar my self and put girder logo as nav bar icon, and make it unclickable when not connected
    layout.title.set_text("Welcome on GirderMedViewer")
    layout.toolbar.height = 75
    layout.icon = vuetify.VBtn(icon="icon")

    with layout.toolbar:
        with vuetify.VBtn(
            fixed=True,
            right=True,
            large=True,
            click='display_authentication = !display_authentication'
        ):
            html.Div("{} {}".format("{{ firstName }} ", "{{ lastName }} "), v_if=("user",))
            html.Div("Log In", v_else=True)
            vuetify.VIcon("mdi-account", v_if=("user",))
            vuetify.VIcon("mdi-login-variant", v_else=True)

    with layout.content:
        with vuetify.VContainer(v_if=("display_authentication",)), vuetify.VCard():
            vuetify.VTextField(
                v_model=("path",),
                label="Girder URL",
                type="input",
                filled=True,
                clearable=True,
                append_icon="mdi-chevron-right",
                click_append=connect,
                click_clear=disconnect
            )
            #TODO add hint

            with vuetify.VContainer(v_if=("api_url",)):
                #TODO test if APIROOT is relevant
                gwc.GirderAuthentication(v_if=("!user",), register=False)

                with vuetify.VRow(v_else=True):
                    with vuetify.VCol(cols=8):
                        html.Div(
                            "Welcome {} {}".format("{{ firstName }} ", "{{ lastName }} "),
                            classes="subtitle-1 mb-1",
                        )
                    with vuetify.VCol(cols=2):
                        vuetify.VBtn(
                            "Log Out",
                            click=ctrl.provider_logout,
                            block=True,
                            color="primary",
                        )
                    with vuetify.VCol(cols=2):
                        vuetify.VBtn(
                            "Go to Viewer",
                            click='display_authentication = false',
                            block=True,
                            color="primary",
                        )

    with layout.drawer:
        gwc.GirderFileManager(
            v_if=("user",),
            v_model=("selected",),
            location=("location",),
            update_location=(update_location, "[$event]"),
            rowclick=(
                handle_rowclick,
                "[$event]"
            ),
        )
        # gwc.GirderDataDetails(
        #     v_if=("user",),
        #     value=("data_details",)
        # )

if __name__ == "__main__":
    if not os.path.exists("tmp"):
        os.mkdir("tmp")
    server.start(port=8081)