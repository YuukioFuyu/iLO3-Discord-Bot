import os
import discord
import time
import requests
import asyncio
import urllib3
import subprocess
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from discord import app_commands
from datetime import datetime

urllib3.disable_warnings()
load_dotenv()

ILO_IP = os.getenv("ILO_IP")
ILO_USER = os.getenv("ILO_USER")
ILO_PASS = os.getenv("ILO_PASS")

GUILD_ID = int(os.getenv("GUILD_ID"))

TOKEN = os.getenv("DISCORD_TOKEN")

BOT_STATUS_TYPE = os.getenv("BOT_STATUS_TYPE","playing")
BOT_STATUS_TEXT = os.getenv("BOT_STATUS_TEXT","iLO Monitor")
BOT_STATUS_STREAM_URL = os.getenv("BOT_STATUS_STREAM_URL","https://twitch.tv/test")


# =========================
# BOT ACTIVITY STATUS
# =========================

def get_activity():

    t = BOT_STATUS_TYPE.lower()


    # ======================
    # AUTO MODE
    # ======================

    if t=="auto":

        s = ilo_status()

        if s is True:
            text="🟢 Server ONLINE"

        elif s is False:
            text="🔴 Server OFFLINE"

        else:
            text="⚪ Server UNKNOWN"

        return discord.Game(name=text)


    # ======================
    # MANUAL MODES
    # ======================

    if t=="playing":
        return discord.Game(name=BOT_STATUS_TEXT)

    if t=="listening":
        return discord.Activity(
            type=discord.ActivityType.listening,
            name=BOT_STATUS_TEXT
        )

    if t=="watching":
        return discord.Activity(
            type=discord.ActivityType.watching,
            name=BOT_STATUS_TEXT
        )

    if t=="competing":
        return discord.Activity(
            type=discord.ActivityType.competing,
            name=BOT_STATUS_TEXT
        )

    if t=="streaming":
        return discord.Streaming(
            name=BOT_STATUS_TEXT,
            url=BOT_STATUS_STREAM_URL
        )

    if t=="custom":
        return discord.CustomActivity(
            name=BOT_STATUS_TEXT
        )

    return discord.Game(name=BOT_STATUS_TEXT)


# =========================
# CORE iLO REQUEST
# =========================

def ilo_latency():

    start=time.time()

    ilo_status()

    end=time.time()

    return f"{round((end-start)*1000,1)} ms"


def ping_latency():

    try:

        p = subprocess.run(
            ["ping","-c","1","-W","1",ILO_IP],
            capture_output=True,
            text=True
        )

        out=p.stdout

        if "time=" in out:

            latency=out.split("time=")[1].split(" ")[0]

            return latency+" ms"

        return "Timeout"

    except:

        return "Error"


def logs_today(xml):

    today = datetime.now().strftime("%m/%d/%Y")

    today_logs=[]
    notset_logs=[]
    all_logs=[]

    lines = xml.split("<EVENT")

    for line in lines:

        date=""
        desc=""
        severity=""

        if 'LAST_UPDATE="' in line:
            date=line.split('LAST_UPDATE="')[1].split('"')[0].strip()

        if 'DESCRIPTION="' in line:
            desc=line.split('DESCRIPTION="')[1].split('"')[0]

        if 'SEVERITY="' in line:
            severity=line.split('SEVERITY="')[1].split('"')[0]


        entry=f"🕒 {date} [{severity}]\n{desc}"


        # =====================
        # TODAY
        # =====================

        if today in date:

            today_logs.append(entry)


        # =====================
        # NOT SET
        # =====================

        elif "[NOT SET]" in date:

            notset_logs.append(entry)


        # =====================
        # ALL
        # =====================

        else:

            all_logs.append(entry)



    # =====================
    # PRIORITY
    # =====================

    if today_logs:
        return today_logs,"today"

    if notset_logs:
        return notset_logs,"notset"

    if all_logs:
        return all_logs,"all"

    return [],"none"


def parse_xml(xml):

    try:
        return ET.fromstring(xml)
    except:
        return None


def parse_ribcl(xml):

    parts = xml.split("<?xml")

    for p in parts[::-1]:

        if "<GET_" in p:

            try:
                return ET.fromstring("<?xml"+p)
            except:
                continue

    return None


def parse_ribcl_value(xml, tag, attr="VALUE"):

    parts = xml.split("<?xml")

    for p in parts:

        try:

            root = ET.fromstring("<?xml"+p)

            node = root.find(f".//{tag}")

            if node is not None:

                return node.get(attr)

        except:
            continue

    return None


def ilo_request(xml):

    try:

        r = requests.post(
            f"http://{ILO_IP}/ribcl",
            data=xml.encode(),
            headers={"Content-Type":"text/xml"},
            verify=False,
            timeout=10
        )

        return r.text

    except Exception as e:

        return f"ERROR: {e}"


def ilo_xml(body):

    return f"""<?xml version="1.0"?>
<RIBCL VERSION="2.0">
 <LOGIN USER_LOGIN="{ILO_USER}" PASSWORD="{ILO_PASS}">
{body}
 </LOGIN>
</RIBCL>
"""

def make_embed(title, description="", color=0x2ecc71):

    e = discord.Embed(
        title=title,
        description=description,
        color=color
    )

    e.set_footer(text=f"iLO3 monitor by Yuuki0 held by Adila raped by Dim")

    return e


# =========================
# POWER FUNCTIONS
# =========================

def ilo_status():

    xml = ilo_xml("""
<SERVER_INFO MODE="read">
<GET_HOST_POWER_STATUS/>
</SERVER_INFO>
""")

    r = ilo_request(xml)

    if 'HOST_POWER="ON"' in r:
        return True

    if 'HOST_POWER="OFF"' in r:
        return False

    return None


def ilo_toggle():

    ilo_request(ilo_xml("""
<SERVER_INFO MODE="write">
<PRESS_PWR_BTN/>
</SERVER_INFO>
"""))


def ilo_on():

    ilo_request(ilo_xml("""
<SERVER_INFO MODE="write">
<SET_HOST_POWER HOST_POWER="Yes"/>
</SERVER_INFO>
"""))


def ilo_off():

    ilo_request(ilo_xml("""
<SERVER_INFO MODE="write">
<SET_HOST_POWER HOST_POWER="No"/>
</SERVER_INFO>
"""))


def ilo_reboot():

    ilo_request(ilo_xml("""
<SERVER_INFO MODE="write">
<RESET_SERVER/>
</SERVER_INFO>
"""))


def ilo_warmboot():

    ilo_request(ilo_xml("""
<SERVER_INFO MODE="write">
<WARM_BOOT_SERVER/>
</SERVER_INFO>
"""))


def ilo_coldboot():

    ilo_request(ilo_xml("""
<SERVER_INFO MODE="write">
<COLD_BOOT_SERVER/>
</SERVER_INFO>
"""))


def ilo_forceoff():

    ilo_request(ilo_xml("""
<SERVER_INFO MODE="write">
<HOLD_PWR_BTN/>
</SERVER_INFO>
"""))


def ilo_reset():

    ilo_request(ilo_xml("""
<RIB_INFO MODE="write">
<RESET_RIB/>
</RIB_INFO>
"""))


# =========================
# INFO FUNCTIONS
# =========================

def ilo_fw():

    return ilo_request(ilo_xml("""
<RIB_INFO MODE="read">
<GET_FW_VERSION/>
</RIB_INFO>
"""))


def ilo_health_raw():

    return ilo_request(ilo_xml("""
<SERVER_INFO MODE="read">
<GET_EMBEDDED_HEALTH/>
</SERVER_INFO>
"""))


def ilo_network():

    return ilo_request(ilo_xml("""
<RIB_INFO MODE="read">
<GET_NETWORK_SETTINGS/>
</RIB_INFO>
"""))


def ilo_servername():

    return ilo_request(ilo_xml("""
<SERVER_INFO MODE="read">
<GET_SERVER_NAME />
</SERVER_INFO>
"""))


# =========================
# LIGHT FUNCTIONS
# =========================

def uid_status():

    xml = ilo_xml("""
<SERVER_INFO MODE="read">
<GET_UID_STATUS/>
</SERVER_INFO>
""")

    r = ilo_request(xml)

    root = parse_ribcl(r)

    if root is None:
        print("UID PARSE FAILED")
        print(r)
        return None

    node = root.find(".//GET_UID_STATUS")

    if node is None:
        print("UID NODE NOT FOUND")
        print(r)
        return None

    state = node.get("UID","").upper()

    if state == "ON":
        return True

    if state == "OFF":
        return False

    print("UNKNOWN UID STATE:",state)

    return None


def uid_set(state):

    s = "Yes" if state else "No"

    ilo_request(ilo_xml(f"""
<SERVER_INFO MODE="write">
<UID_CONTROL UID="{s}"/>
</SERVER_INFO>
"""))


# =========================
# LOG FUNCTIONS
# =========================

def ilo_eventlog():

    return ilo_request(ilo_xml("""
<RIB_INFO MODE="read">
<GET_EVENT_LOG/>
</RIB_INFO>
"""))


async def wait_status(target):

    for i in range(120):

        if ilo_status() == target:
            return True

        await asyncio.sleep(1)

    return False


# =========================
# BOT
# =========================

class Bot(discord.Client):

    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):

        guild = discord.Object(id=GUILD_ID)

        commands = [

        status,
        power,

        info_cmd,
        ilo_cmd,
        health_cmd,
        network,

        uidtoggle,

        eventlog

        ]

        for c in commands:
            self.tree.add_command(c,guild=guild)

        await self.tree.sync(guild=guild)


bot = Bot()


@bot.event
async def on_ready():

    # last=None

    while True:

        # s = ilo_status()

        # if s!=last:

        await bot.change_presence(
            activity=get_activity(),
            status=discord.Status.online
        )

            # last=s

        await asyncio.sleep(30)


# =========================
# POWER COMMANDS
# =========================

@app_commands.command(name="status",description="🟢 Check server power status")
async def status(i:discord.Interaction):

    await i.response.defer()

    s = ilo_status()

    latency = ping_latency()

    if s:
        msg="🟢 ACTIVE"
        color=0x2ecc71
    else:
        msg="🔴 INACTIVE"
        color=0xe74c3c

    e = make_embed(
        "Server Status",
        msg,
        color
    )

    e.add_field(
        name="Ping",
        value=latency,
        inline=True
    )

    e.add_field(
        name="iLO API",
        value=ilo_latency(),
        inline=True
    )

    e.add_field(
        name="IP",
        value=ILO_IP,
        inline=True
    )

    await i.followup.send(embed=e)


@app_commands.command(name="power",description="⚡ Power control")

@app_commands.describe(action="Power action (default = momentary press)")

@app_commands.choices(action=[

    app_commands.Choice(name="Power ON", value="on"),
    app_commands.Choice(name="Power OFF", value="off"),
    app_commands.Choice(name="Reboot", value="reboot"),
    app_commands.Choice(name="Warm Boot", value="warmboot"),
    app_commands.Choice(name="Cold Boot", value="coldboot"),
    app_commands.Choice(name="Force OFF", value="forceoff")

])

async def power(
    i:discord.Interaction,
    action:app_commands.Choice[str] = None
):

    await i.response.defer()


    # =====================
    # DEFAULT = MOMENTARY
    # =====================

    if action is None:

        ilo_toggle()

        await i.followup.send(
            "⚪ Momentary Power Button Pressed"
        )

        return


    act = action.value


    if act=="on":

        ilo_on()
        msg="🟢 Power ON"


    elif act=="off":

        ilo_off()
        msg="🔴 Power OFF"


    elif act=="reboot":

        ilo_reboot()
        msg="♻ Reboot"


    elif act=="warmboot":

        ilo_warmboot()
        msg="♻ Warm Boot"


    elif act=="coldboot":

        ilo_coldboot()
        msg="⚠ Cold Boot"


    elif act=="forceoff":

        ilo_forceoff()
        msg="⛔ Force OFF"


    else:

        msg="Unknown action"


    await i.followup.send(msg)


# =========================
# INFO COMMANDS
# =========================

@app_commands.command(name="ilo",description="📟 iLO firmware info")

@app_commands.describe(action="Action (optional)")

@app_commands.choices(action=[

    app_commands.Choice(name="Reset iLO", value="reset")

])

async def ilo_cmd(
    i:discord.Interaction,
    action:app_commands.Choice[str] = None
):


    # =====================
    # RESET MODE
    # =====================

    if action and action.value=="reset":

        await i.response.send_message("🔧 Restarting iLO")

        ilo_reset()

        return


    # =====================
    # DEFAULT = INFO
    # =====================

    await i.response.defer()

    xml = ilo_fw()

    root=parse_ribcl(xml)

    fw=root.find(".//GET_FW_VERSION")


    e = make_embed("📀 iLO Firmware")

    e.add_field(
        name="Version",
        value=fw.get("FIRMWARE_VERSION"),
        inline=True
    )

    e.add_field(
        name="Date",
        value=fw.get("FIRMWARE_DATE"),
        inline=True
    )

    e.add_field(
        name="Controller",
        value=fw.get("MANAGEMENT_PROCESSOR"),
        inline=True
    )

    e.add_field(
        name="License",
        value=fw.get("LICENSE_TYPE"),
        inline=True
    )

    await i.followup.send(embed=e)


@app_commands.command(name="info",description="🖥 Server hostname info")
async def info_cmd(i:discord.Interaction):

    await i.response.defer()

    xml = ilo_servername()

    hostname = parse_ribcl_value(xml,"SERVER_NAME")

    if hostname is None:

        await i.followup.send(
            "⚠ Unable to read server hostname"
        )

        return


    e = make_embed("🖥 Server Info")

    e.add_field(
        name="Hostname",
        value=hostname,
        inline=False
    )

    await i.followup.send(embed=e)


@app_commands.command(name="health",description="❤️ Hardware health info")

@app_commands.describe(type="Health data type  (default = summary)")

@app_commands.choices(type=[

    app_commands.Choice(name="Temperature",value="temp"),
    app_commands.Choice(name="Fans",value="fan"),
    app_commands.Choice(name="Power Supplies",value="power")

])

async def health_cmd(
    i:discord.Interaction,
    type:app_commands.Choice[str] = None
):

    await i.response.defer()

    xml = ilo_health_raw()

    root = parse_ribcl(xml)


    # =====================
    # DEFAULT = SUMMARY
    # =====================

    if type is None:

        h = root.find(".//HEALTH_AT_A_GLANCE")

        e = make_embed("❤️ Hardware Health")

        e.add_field(
            name="Fans",
            value=h.find("FANS").get("STATUS"),
            inline=True
        )

        e.add_field(
            name="Temperature",
            value=h.find("TEMPERATURE").get("STATUS"),
            inline=True
        )

        e.add_field(
            name="Power",
            value=h.find("POWER_SUPPLIES").get("STATUS"),
            inline=True
        )

        await i.followup.send(embed=e)

        return


    t = type.value


    # =====================
    # TEMP
    # =====================

    if t=="temp":

        temps=root.findall(".//TEMP")

        e=make_embed("🌡 Temperature")

        txt=""

        for temp in temps:

            txt+=f"**{temp.find('LOCATION').get('VALUE')}** → "
            txt+=f"{temp.find('CURRENTREADING').get('VALUE')}°C "
            txt+=f"({temp.find('STATUS').get('VALUE')})\n"

        e.description=txt[:4000]

        await i.followup.send(embed=e)

        return


    # =====================
    # FAN
    # =====================

    if t=="fan":

        fans=root.findall(".//FAN")

        e=make_embed("🌀 Fans")

        txt=""

        for f in fans:

            txt+=f"**{f.find('LABEL').get('VALUE')}** → "
            txt+=f"{f.find('STATUS').get('VALUE')} "
            txt+=f"({f.find('SPEED').get('VALUE')}%)\n"

        e.description=txt[:4000]

        await i.followup.send(embed=e)

        return


    # =====================
    # POWER SUPPLY + VRM
    # =====================

    if t=="power":

        supplies=root.findall(".//SUPPLY")

        vrm=root.findall(".//MODULE")

        e=make_embed("⚡ Power System")


        supply_txt=""

        for s in supplies:

            supply_txt+=f"🔌 {s.find('LABEL').get('VALUE')} → "
            supply_txt+=f"{s.find('STATUS').get('VALUE')}\n"

        if supply_txt=="":
            supply_txt="No data"


        e.add_field(
            name="Power Supplies",
            value=supply_txt,
            inline=False
        )


        vrm_txt=""

        for v in vrm:

            vrm_txt+=f"⚙ {v.find('LABEL').get('VALUE')} → "
            vrm_txt+=f"{v.find('STATUS').get('VALUE')}\n"

        if vrm_txt=="":
            vrm_txt="No data"


        e.add_field(
            name="VRM Modules",
            value=vrm_txt,
            inline=False
        )


        await i.followup.send(embed=e)


@app_commands.command(name="network",description="🌐 Network settings")
async def network(i:discord.Interaction):

    await i.response.defer()

    xml=ilo_network()

    root=parse_ribcl(xml)

    n=root.find(".//GET_NETWORK_SETTINGS")

    e=make_embed("🌐 Network Settings")

    e.add_field(
        name="IP Address",
        value=n.find("IP_ADDRESS").get("VALUE"),
        inline=True
    )

    e.add_field(
        name="Subnet",
        value=n.find("SUBNET_MASK").get("VALUE"),
        inline=True
    )

    e.add_field(
        name="Gateway",
        value=n.find("GATEWAY_IP_ADDRESS").get("VALUE"),
        inline=True
    )

    e.add_field(
        name="MAC",
        value=n.find("MAC_ADDRESS").get("VALUE"),
        inline=True
    )

    e.add_field(
        name="DHCP",
        value=n.find("DHCP_ENABLE").get("VALUE"),
        inline=True
    )

    e.add_field(
        name="DNS Name",
        value=n.find("DNS_NAME").get("VALUE"),
        inline=True
    )

    await i.followup.send(embed=e)


# =========================
# LIGHT COMMANDS
# =========================

@app_commands.command(name="uid",description="💡 UID LED control")

@app_commands.describe(action="UID Action (default = toggle)")

@app_commands.choices(action=[

    app_commands.Choice(name="Status", value="status"),
    app_commands.Choice(name="ON", value="on"),
    app_commands.Choice(name="OFF", value="off")

])

async def uidtoggle(
    i:discord.Interaction,
    action:app_commands.Choice[str] = None
):

    await i.response.defer()


    # =====================
    # DEFAULT = TOGGLE
    # =====================

    if action is None:

        initial = uid_status()

        if initial is None:
            await i.followup.send("⚠ Unable to read UID status")
            return

        uid_set(not initial)

        for _ in range(10):

            await asyncio.sleep(1)

            new_state = uid_status()

            if new_state != initial:
                break

        if new_state is None:
            await i.followup.send("⚠ UID toggle uncertain")
            return

        emoji = "🔵" if new_state else "⚫"
        state = "ON" if new_state else "OFF"

        await i.followup.send(
            f"{emoji} UID LED → {state}"
        )

        return


    act = action.value


    # =====================
    # STATUS
    # =====================

    if act=="status":

        s = uid_status()

        if s is None:
            await i.followup.send("⚠ Unable to read UID status")
            return

        emoji = "🔵" if s else "⚫"
        state = "ON" if s else "OFF"

        await i.followup.send(
            f"{emoji} UID LED → {state}"
        )

        return


    # =====================
    # FORCE ON
    # =====================

    if act=="on":

        uid_set(True)

        await asyncio.sleep(2)

        await i.followup.send(
            "🔵 UID LED → ON"
        )

        return


    # =====================
    # FORCE OFF
    # =====================

    if act=="off":

        uid_set(False)

        await asyncio.sleep(2)

        await i.followup.send(
            "⚫ UID LED → OFF"
        )

        return


# =========================
# LOG COMMANDS
# =========================

@app_commands.command(name="logs",description="📜 Server event log")
async def eventlog(i:discord.Interaction):

    await i.response.defer()

    xml=ilo_eventlog()

    logs,mode=logs_today(xml)


    if mode=="today":
        title="📜 Event Log (Today)"

    elif mode=="notset":
        title="📜 Event Log (Clock Error)"

    elif mode=="all":
        title="📜 Event Log (All)"

    else:
        title="📜 Event Log"


    e=make_embed(title)


    if logs:

        text="\n\n".join(logs[:10])

        e.description=text

        e.add_field(
            name="Entries",
            value=str(len(logs)),
            inline=True
        )

    else:

        e.description="No logs found"


    await i.followup.send(embed=e)


bot.run(TOKEN)
