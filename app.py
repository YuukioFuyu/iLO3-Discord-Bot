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

    logs=[]

    lines = xml.split("<EVENT")

    for line in lines:

        if today in line:

            date=""
            desc=""
            severity=""

            if 'LAST_UPDATE="' in line:
                date=line.split('LAST_UPDATE="')[1].split('"')[0]

            if 'DESCRIPTION="' in line:
                desc=line.split('DESCRIPTION="')[1].split('"')[0]

            if 'SEVERITY="' in line:
                severity=line.split('SEVERITY="')[1].split('"')[0]

            logs.append(
                f"🕒 {date} [{severity}]\n{desc}"
            )

            if len(logs)>=10:
                break

    return logs


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

    e.set_footer(text="iLO3 Monitor")

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
        momentary,
        startup,
        shutdown,
        reboot,
        warmboot,
        coldboot,
        forceoff,
        ilo_reset_cmd,

        ilo_cmd,
        health,
        temp,
        fan,
        power_read,
        network,

        uidtoggle,

        eventlog

        ]

        for c in commands:
            self.tree.add_command(c,guild=guild)

        await self.tree.sync(guild=guild)


bot = Bot()


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
        name="Power",
        value=msg,
        inline=True
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


@app_commands.command(name="momentary",description="⚪️ Press power button")
async def momentary(i:discord.Interaction):

    await i.response.send_message("⚪️ Pressing button")

    ilo_toggle()


@app_commands.command(name="startup",description="🟢 Power ON server")
async def startup(i:discord.Interaction):

    await i.response.send_message("🟢 Starting server")

    ilo_on()


@app_commands.command(name="shutdown",description="🔴 Power OFF server")
async def shutdown(i:discord.Interaction):

    await i.response.send_message("🔴 Shutting down")

    ilo_off()


@app_commands.command(name="reboot",description="♻ Normal reboot")
async def reboot(i:discord.Interaction):

    await i.response.send_message("♻ Rebooting")

    ilo_reboot()


@app_commands.command(name="warmboot",description="♻ Fast reboot")
async def warmboot(i:discord.Interaction):

    await i.response.send_message("♻ Warm boot")

    ilo_warmboot()


@app_commands.command(name="coldboot",description="⚠ Power cycle reboot")
async def coldboot(i:discord.Interaction):

    await i.response.send_message("⚠ Cold boot")

    ilo_coldboot()


@app_commands.command(name="forceoff",description="⛔ Force shutdown")
async def forceoff(i:discord.Interaction):

    await i.response.send_message("⛔ Force power off")

    ilo_forceoff()


@app_commands.command(name="ilo_reset",description="🔧 Restart iLO only")
async def ilo_reset_cmd(i:discord.Interaction):

    await i.response.send_message("🔧 Restarting iLO")

    ilo_reset()


# =========================
# INFO COMMANDS
# =========================

@app_commands.command(name="ilo",description="📟 iLO firmware info")
async def ilo_cmd(i:discord.Interaction):

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


@app_commands.command(name="health",description="❤️ Overall Health")
async def health(i:discord.Interaction):

    await i.response.defer()

    xml=ilo_health_raw()

    root=parse_ribcl(xml)

    h=root.find(".//HEALTH_AT_A_GLANCE")

    e=make_embed("❤️ Hardware Health")

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


@app_commands.command(name="temp",description="🌡 Temperature sensors")
async def temp(i:discord.Interaction):

    await i.response.defer()

    xml=ilo_health_raw()

    root=parse_ribcl(xml)

    temps=root.findall(".//TEMP")

    e=make_embed("🌡 Temperature")

    txt=""

    for t in temps:

        txt+=f"**{t.find('LOCATION').get('VALUE')}** → "
        txt+=f"{t.find('CURRENTREADING').get('VALUE')}°C "
        txt+=f"({t.find('STATUS').get('VALUE')})\n"

    e.description=txt[:4000]

    await i.followup.send(embed=e)


@app_commands.command(name="fan",description="🌀 Fan status")
async def fan(i:discord.Interaction):

    await i.response.defer()

    xml=ilo_health_raw()

    root=parse_ribcl(xml)

    fans=root.findall(".//FAN")

    e=make_embed("🌀 Fans")

    txt=""

    for f in fans:

        txt+=f"**{f.find('LABEL').get('VALUE')}** → "
        txt+=f"{f.find('STATUS').get('VALUE')} "
        txt+=f"({f.find('SPEED').get('VALUE')}%)\n"

    e.description=txt[:4000]

    await i.followup.send(embed=e)


@app_commands.command(name="power",description="⚡ Power supplies and VRM")
async def power_read(i:discord.Interaction):

    await i.response.defer()

    xml=ilo_health_raw()

    root=parse_ribcl(xml)

    supplies=root.findall(".//SUPPLY")

    vrm=root.findall(".//MODULE")

    e=make_embed("⚡ Power System")

    # ----------------
    # POWER SUPPLY
    # ----------------

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

    # ----------------
    # VRM
    # ----------------

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

@app_commands.command(name="uid",description="💡 Toggle UID LED")
async def uidtoggle(i:discord.Interaction):

    await i.response.defer()

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


# =========================
# LOG COMMANDS
# =========================

@app_commands.command(name="eventlog",description="📜 Server event log (today)")
async def eventlog(i:discord.Interaction):

    await i.response.defer()

    xml=ilo_eventlog()

    logs=logs_today(xml)

    e=make_embed("📜 Event Log (Today)")

    if logs:

        text="\n\n".join(logs[:10])

        e.description=text

        e.add_field(
            name="Entries Today",
            value=str(len(logs)),
            inline=True
        )

    else:

        e.description="🟢 No events today"

    await i.followup.send(embed=e)


bot.run(TOKEN)
