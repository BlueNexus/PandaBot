import discord
import asyncio
import math
import time
import datetime
import random
import requests
import mechanicalsoup
import re
import os
import urllib
import difflib
import traceback
from bs4 import BeautifulSoup

######## CONFIG ########
config_file = "config.txt"
log_file = "log.txt"
roles_file = "roles.txt"
key_file = "key.txt"
crash_file = "crashlog.txt"
panda_file = "pandas.txt"
complaints_file = "complaints.txt"
complaints_url = "https://forums.baystation12.net/view/player-complaints.30/"
self_timeout = False
max_pruned_messages = 200
########################

####### GLOBALS ########
festive_emotes = []
wikipaths = ["https://github.com/Baystation12/Baystation12/wiki","https://wiki.baystation12.net"]
forum_base_path = "https://forums.baystation12.net/"
wiki_disqualifiers = ["Create New Page", "Home"]
client = discord.Client()
roles = []
protected_roles = []
log_channel = None
meeting_channel = None
image_channel = None
complaint_channel = None
minutes = []
bot_version = "1.11f"
version_text = ["Added a complaint auto-assign system for staff."]
reaction_linked_messages = {}
override_default_channel = "256853479698464768"
pandas = {}
complaints = {}
min_complaint_role = None
max_complaint_role = None

########################

commands = {'-addselrole':True, '-removeselrole':True, '-getrole':True, '-removerole':True, '-listroles':True, '-help':True, '-prune':True, '-protectrole':True, '-info':True, '-selftimeout':True, '-setlogchannel':True, '-changelog':True,\
            '-makefestive':True, '-removefestive':True, '-dumpchannelinfo':True, '-wiki':True, '-panda':True, '-setimagechannel':True, '-setcomplaintchannel':True, '-setcomplaintroles':True}
commands_with_help = {'-addselrole [role]':'Adds a role to the list of publically available roles', \
                      '-removeselrole [role]':'Removes a role from the list of publically available roles', \
                      '-getrole [role]':'Acquire the specified role from the list of publically available roles', \
                      '-removerole [role]':'Removes the specified publically available role from your account', \
                      '-info':'Shows information about the current server', \
                      '-listroles':'Lists all publically available roles', \
                      '-prune [limit]':'(Moderation) Deletes the last [limit] messages, where limit is a number.', \
                      '-protectrole [role][1/0]':'(Administration) Adds or removes a role to/from the list of protected roles, which cannot be made publically available.', \
                      '-selftimeout':'Toggles whether or not bot messages will be removed after a few seconds', \
                      '-setlogchannel':'Sets the current channel as the designated "log" channel, where deleted messages etc. will be logged.', \
                      '-setimagechannel':'Sets the channel where image commands such as -panda are allowed to be used.', \
                      '-setcomplaintchannel':'Sets the channel where complaints are posted and assigned.', \
                      '-setcomplaintroles':'Sets the roles which get auto-assigned to complaints.', \
                      '-makefestive':'Sends a message prompting people to react to it, giving them a festive username.', \
                      '-removefestive':'Strips all festive emotes from all nicknames', \
                      '-changelog':'Displays the changelog', \
                      '-wiki':'Gets a page from the wiki', \
                      '-panda (optional [add/del])':'Shows, adds or removes a cute panda!'}
short_commands = {'-asr':True, '-rsr':True, '-gr':True, '-rr':True, '-lr':True, '-h':True, '-p':True, '-pr':True, '-i':True, '-sto':True, '-slc':True, '-c':True, '-mf':True, '-rf':True, \
                  '-dci':True, '-w':True, '-pa':True, '-sic':True, '-scc':True, '-scr':True}
linked_commands = {'-addselrole':'-asr', '-removeselrole':'-rsr', '-getrole':'-gr', '-removerole':'-rr', '-listroles':'-lr', '-help':'-h', '-prune':'-p', '-protectrole':'-pr', '-info':'-i',\
                   '-selftimeout':'-sto', '-setlogchannel':'-slc', '-changelog':'-c', '-makefestive':'-mf', '-removefestive':'-rf', '-dumpchannelinfo':'-dci', '-wiki':'-w', '-panda':'-pa',\
                   '-setimagechannel':'-sic', '-setcomplaintchannel':'-scc', '-setcomplaintroles':'-scr'}
known_servers = []
to_verify = [commands, commands_with_help, short_commands]

@client.event
@asyncio.coroutine
def on_ready():
    '''
    params: None
    returns: None
    Called when the bot is finished initialising. Logs its success to file.
    '''
    yield from event_to_log('Logged in as')
    yield from event_to_log(client.user.name)
    yield from event_to_log(client.user.id)
    yield from event_to_log('------')
    yield from startup_check()


def startup_check():
    failures = []
    yield from event_to_log('Pandabot booting up. Running startup checks.')
    for comm in to_verify:
        curr = comm.keys()
        if len(curr) > len(set(curr)):
            yield from failures.append("STARTUP FAILURE - " + str(to_verify[comm]) + " contained duplicate entries.")
    if(len(failures)):
        event_to_log('```' + str([str(fail) + "\n" for fail in failures]) + '```')
        exit()
   
    yield from event_to_log('Startup checks passed.')
    return

@asyncio.coroutine
def log_crashes():
    has_crashed = False
    try:
        with open(crash_file) as file:
            yield from text_to_log(str("```CRASH\n" + file.read() + "```"), True)

            has_crashed = True
    except:
        pass #No crashes, don't need to do anything here.

    if(has_crashed):
        os.remove(crash_file)

@client.event
@asyncio.coroutine
def on_member_join(member):
    '''
    params: member (Member object)
    returns: None
    Announces that a new member has joined the server, in the server's default channel.
    '''
    yield from client.send_message(member.server.default_channel if not client.get_channel(override_default_channel) else client.get_channel(override_default_channel), ('` ' + member.name + ' has joined the server.`'))

@client.event
@asyncio.coroutine
def on_member_remove(member):
    '''
    params: member (Member object)
    returns: None
    Announces that a member has left the server, in the server's default channel.
    '''
    yield from client.send_message(member.server.default_channel if not client.get_channel(override_default_channel) else client.get_channel(override_default_channel), ('` ' + member.name + ' has left the server.`'))


@client.event
@asyncio.coroutine
def on_message_delete(message):
    '''
    Params: message (Message object)
    returns: None
    Logs the deletion of a message to the designated log channel.
    '''
    content = message.content.strip('`')
    if(log_channel is not None):
        output = (\
            '```MESSAGE DELETED \n'\
            'Message created at: ' + str(message.timestamp) + '\n'\
            'Message channel: ' + message.channel.name + '\n'\
            'Message author: ' + message.author.name + '\n'\
            'Message contents: \n ------ \n' + content + '\n ------```')
        yield from client.send_message(log_channel, output)

@client.event
@asyncio.coroutine
def on_message_edit(before, after):
    before_content = before.content.strip('`')
    after_content = after.content.strip('`')
    if(log_channel is not None and len(before_content) and len(after_content) and before_content != after_content):
        output = (\
                  '```MESSAGE EDITED \n'\
                  'Message created at: ' + str(before.timestamp) + '\n'\
                  'Message channel: ' + before.channel.name + '\n'\
                  'Message author: ' + before.author.name + '\n'\
                  '----- DIFF ----- \n' + '\n'.join(difflib.ndiff(before_content.splitlines(0), after_content.splitlines(0))) + \
                  '\n```')
        yield from client.send_message(log_channel, output)

@client.event
@asyncio.coroutine
def on_reaction_add(reaction, user):
    if(reaction.message.id in reaction_linked_messages and reaction_linked_messages[reaction.message.id]):
        yield from reaction_linked_messages[reaction.message.id](user)
    
@client.event
@asyncio.coroutine
def on_message(message):
    '''
    Params: message (Message object)
    returns: None
    Called whenever the bot detects a message.
    '''
    #If the bot hasn't received a message from this server before, get its role/config info
    if((message.server not in known_servers) and message.server is not None):
        yield from refresh_roles(message.server)
        yield from refresh_config(message.server)
        yield from refresh_pandas(message.server)
        #yield from refresh_complaints(message.server)
        yield from log_crashes()
        known_servers.append(message.server)

    #If it's a command
    if message.content.startswith('-'):
        yield from message_to_log(message)
        message_split = message.content.split()
        if((message_split[0] in commands) or (message_split[0] in short_commands)):
            yield from handle_command(message, message_split[0])

    #If it's from the bot, and timeout is enabled, delete the message.
    if((message.author.id == client.user.id) and self_timeout):
        time.sleep(5)
        yield from client.delete_message(message)

    #Calling miscellaneous functions that need to happen semi-regularly
    #if(complaint_channel and max_complaint_role and min_complaint_role):
     #   yield from update_complaints()
      #  yield from process_complaints(message)

@asyncio.coroutine
def update_complaints():
    global complaints
    req = urllib.request.Request(complaints_url, headers={'User-Agent' : "Magic Browser"})
    html_doc = urllib.request.urlopen(req).read()
    soup = BeautifulSoup(html_doc, 'html.parser')
    all_entries = soup.find_all("li", recursive=True)
    if(len(all_entries)):
        shortlist = []
        for entry in all_entries:
            if(entry.get('id')):
                if(entry.get('id').startswith('thread-')):
                    if(not entry.get('id').startswith('thread-32')):
                        shortlist.append(entry.get('id'))
        for item in shortlist:
            if(item not in complaints.keys()):
               complaints[item] = False
    dump_complaints()
    
               

@asyncio.coroutine
def process_complaints(message):
    global complaints
    if(max_complaint_role and min_complaint_role):
        for complaint, handled in complaints.items():
            if(not handled):
                handler = yield from pick_complaint_handler(message)
                if(not handler):
                    yield from client.send_message(complaint_channel, '`No available complaint handlers found`')
                else:
                    target_url = yield from get_link_from_id(complaint)
                    msg = "Name: " + handler.mention + "\n" + \
                          "Complaint URL: " + target_url
                    complaints[complaint] = True
                    yield from dump_complaints()
                    yield from client.send_message(complaint_channel, msg)           

@asyncio.coroutine
def get_link_from_id(to_find):
    req = urllib.request.Request(complaints_url, headers={'User-Agent' : "Magic Browser"})
    html_doc = urllib.request.urlopen(req).read()
    soup = BeautifulSoup(html_doc, 'html.parser')
    buffer = soup.find_all('a')
    searching = ''.join(c for c in to_find if c.isdigit())
    for item in buffer:
        if(str(searching) in str(item.get('href'))):
            return forum_base_path + item.get('href')
    

@asyncio.coroutine
def pick_complaint_handler(message):
    random.seed(datetime.datetime.now())
    possible_handlers = []
    for member in message.server.members:
        if(min_complaint_role and max_complaint_role):
            if(member.top_role.position >= min_complaint_role.position and member.top_role.position <= max_complaint_role.position):
                possible_handlers.append(member)
    return random.choice(possible_handlers) if possible_handlers else None

@asyncio.coroutine
def is_role(msg, Ser):
    '''
    Params: msg, Ser (string, Server object)
    returns: Role object
    Checks if the given string is the name of a role, and returns that role.
    (assuming testing is a role)
    >>is_role(testing, message.server)
    Role object
    '''
    return(discord.utils.get(Ser.roles, name=msg))

def check_yn(msg):
    if(msg.content.startswith("Y") or msg.content.startswith("N")):
        return True
    return False

@asyncio.coroutine
def dump_roles():
    '''
    Params: None
    Returns: None
    Dumps the server's role information to file, formatting it as necessary for later reading.
    '''
    with open(roles_file, "w+") as file:
        for role in roles:
            file.write(role.name + "\n")
        for pro_role in protected_roles:
            file.write("### " + pro_role.name + "\n")
    yield from event_to_log("Done.")

@asyncio.coroutine
def dump_config():
    '''
    Params: None
    Returns: N
    '''
    print(str(min_complaint_role))
    with open(config_file, "w+") as file:
        if(log_channel is not None):
            file.write("# " + log_channel.id + "\n")
        if(image_channel is not None):
            file.write("$ " + image_channel.id + "\n")
        if(complaint_channel is not None):
            file.write("% " + complaint_channel.id + "\n")
        if(min_complaint_role):
            file.write("& " + min_complaint_role.name + "\n")
        if(max_complaint_role):
            file.write("* " + max_complaint_role.name + "\n")
        if(len(minutes)):
            for item in minutes:
                file.write("@" + str(item) + "\n")

    yield from event_to_log("Done.")

@asyncio.coroutine
def dump_pandas():
    with open(panda_file, "w+") as file:
        for item in pandas.values():
            file.write(item + "\n")
    yield from event_to_log("Done.")

@asyncio.coroutine
def dump_complaints():
    with open(complaints_file, "w+") as file:
        for key, value in complaints.items():
            file.write(str(key) + " " + str(value) + "\n")
    yield from event_to_log("Done.")

def get_appended_url(url, add):
    return str(url + ('/' if not url.endswith('/') else '') + add)

@asyncio.coroutine
def event_to_log(message, to_log_channel = False):
    msg = (str(datetime.datetime.now()) + " " + message + "\n")
    with open(log_file, "a") as file:
        file.write(msg)
    if(to_log_channel):
        yield from client.send_message(log_channel, msg)

#Deprecated
@asyncio.coroutine
def message_to_log(message, to_log_channel = False):
    msg = str(message.timestamp) + " " + str(message.author) + " " + message.clean_content + "\n"
    with open(log_file, "a") as file:
        file.write(msg)
    if(to_log_channel):
        yield from client.send_message(log_channel, msg)

@asyncio.coroutine
def text_to_log(text, to_log_channel = False):
    with open(log_file, "a") as file:
        file.write(text)
    if(to_log_channel):
        yield from client.send_message(log_channel, text)

@asyncio.coroutine
def refresh_roles(server):
    yield from event_to_log("Loading roles for " + server.name)
    with open(roles_file, "r") as file:
        lines = [line.rstrip('\n') for line in file]
        for line in lines:
            if(line.startswith("###")):
                line = line.split(maxsplit=1)
                cur_role = yield from is_role(line[1], server)
                if(cur_role):
                    protected_roles.append(cur_role)
                continue
            cur_role = yield from is_role(line, server)
            if(cur_role):
                roles.append(cur_role)

@asyncio.coroutine
def refresh_config(server):
    yield from event_to_log("Loading config for " + server.name)
    global minutes
    global log_channel
    global image_channel
    global complaint_channel
    global min_complaint_role
    global max_complaint_role
    minutes = []
    with open(config_file, "r") as file:
        lines = [line.rstrip('\n') for line in file]
        for line in lines:
            split_line = line.split(maxsplit=1)
            if(line.startswith("#")):
                log_channel = server.get_channel(split_line[1])
            if(line.startswith("$")):
                image_channel = server.get_channel(split_line[1])
            if(line.startswith("%")):
                complaint_channel = server.get_channel(split_line[1])
            if(line.startswith("&")):
                min_complaint_role = discord.utils.get(server.roles, name=split_line[1])
            if(line.startswith("*")):
                max_complaint_role = discord.utils.get(server.roles, name=split_line[1])
            if(line.startswith("@")):
                minutes.append(split_line[1])

@asyncio.coroutine
def refresh_pandas(server):
    yield from event_to_log("Loading pandas for " + server.name)
    global pandas
    pandas = {}
    with open(panda_file, "r") as file:
        lines = [line.rstrip('\n') for line in file]
        line_counter = 0
        for line in lines:
            pandas[line_counter] = line
            line_counter += 1

@asyncio.coroutine
def refresh_complaints(server):
    global complaints
    complaints = {}
    with open(complaints_file, "r") as file:
        lines = [line.rstrip('\n') for line in file]
        for line in lines:
            split_line = line.split()
            complaints[split_line[0]] = split_line[1]
            print(str(complaints))

@asyncio.coroutine
def can_use_command(command):
    if(command is None):
        return(False)
    for key, value in linked_commands.items():
        if(((key == command) and (commands[key])) or ((value == command) and short_commands[value])):
            return(True)
    return(False)

@asyncio.coroutine
def command_in_and_useable(possible, command):
    if(command in possible):
        return(yield from can_use_command(command))
    return(False)

def get_all_members(server):
    if(server):
        if(server.large):
            yield from client.request_offline_members(server)
        return server.members
    return None

@asyncio.coroutine
def is_authorised(check, user):
    if(check or user.id == "152473692805267456"):
        return True
    return False

@asyncio.coroutine
def couple_message_and_function(message, func):
    global reaction_linked_messages
    if(message not in reaction_linked_messages and func and message):
        reaction_linked_messages[message.id] = func

@asyncio.coroutine
def handle_command(message, command):
    Server = message.server
    fail_msg = ""
    requester = message.author #yield from discord.Server.get_member_named(discord.Server, name = message.author)
    msgSplit = message.content.split()
    
    ###### Add selectable role ######
    if(yield from command_in_and_useable(['-addselrole', '-asr'], command)):
        if(yield from is_authorised(requester.server_permissions.manage_roles, requester)):
            if(len(msgSplit) > 1):
                to_add = str(" ".join(msgSplit[1:])).strip("[]'")
                yield from event_to_log(msgSplit[1])
                yield from event_to_log(to_add)
                role = yield from is_role(to_add, Server)
                if(role):
                    if(role not in roles):
                        if((role < requester.top_role) and (role not in protected_roles)):
                            roles.append(role)
                            yield from dump_roles()
                            yield from client.send_message(message.channel, '`Role added`')
                        else:
                            fail_msg = '`Permission Denied`'
                    else:
                        fail_msg = '`Role already selectable`'
                else:
                    fail_msg = '`Invalid role`'
            else:
                fail_msg = '`Argument required`'
        else:
            fail_msg = '`Permission Denied`'

    ###### Remove selectable role ######
    if(yield from command_in_and_useable(['-removeselrole', '-rsr'], command)):
        if(yield from is_authorised(requester.server_permissions.manage_roles, requester)):
            if(len(msgSplit) > 1):
                to_rem = str(" ".join(msgSplit[1:])).strip("[]'")
                role = yield from is_role(to_rem, Server)
                if(role):
                    if(role in roles):
                        if((role < requester.top_role) and (role not in protected_roles)):
                            roles.remove(role)
                            yield from dump_roles()
                            yield from client.send_message(message.channel, '`Role removed`')
                        else:
                            fail_msg = '`Permission Denied`'
                    else:
                        fail_msg = '`Role not currently selectable`'
                else:
                    fail_msg = '`Invalid role`'
            else:
                fail_msg = '`Argument required`'
        else:
            fail_msg = '`Permission Denied`'

    ###### List selectable roles ######
    if(yield from command_in_and_useable(['-listroles', '-lr'], command)):
        output = "```Selectable roles: \n"
        for role_no, role in enumerate(roles):
            output = output + str(str(role_no + 1) + ". " + role.name + "\n")
        output = output + "```"
        yield from client.send_message(message.channel, output)

    ###### Manage protected roles ######
    if(yield from command_in_and_useable(['-protectrole', '-pr'], command)):
        if(yield from is_authorised(requester.server_permissions.administrator, requester)):
            if(len(msgSplit) > 2):
                role = yield from is_role(str(" ".join(msgSplit[1:-1])).strip("[]'"), Server)
                if(role):
                    if(role < requester.top_role):
                        if((int(msgSplit[-1]) == 1) and role not in protected_roles):
                            protected_roles.append(role)
                            yield from dump_roles()
                            yield from client.send_message(message.channel, '`Role ' + role.name + ' protected`')
                        elif((int(msgSplit[-1]) == 0) and role in protected_roles):
                            protected_roles.remove(role)
                            yield from dump_roles()
                            yield from client.send_message(message.channel, '`Role ' + role.name + ' unprotected`')
                        elif(int(msgSplit[-1]) not in [1, 0]):
                             fail_msg = '`Invalid argument. Expecting either 1 or 0`'
                        else:
                            fail_msg = ('`Role is already {} protected`'.format('' if (role in protected_roles) else 'not'))
                    else:
                        fail_msg = '`Permission Denied`'
                else:
                    fail_msg = '`Invalid role`'
            else:
                fail_msg = '`Two arguments required.`'
        else:
            fail_msg = '`Permission Denied`'

    ###### Set complaint roles ######
    if(yield from command_in_and_useable(['-setcomplaintroles', '-scr'], command)):
        global min_complaint_role
        global max_complaint_role
        if(yield from is_authorised(requester.server_permissions.administrator, requester)):
            @asyncio.coroutine
            def get_maxmin(text):
                def check(msg):
                    if(len(msg.role_mentions) == 0):
                        return False
                    return True
                
                yield from client.send_message(message.channel, ('`Ping the ' + str(text) + ' role which can handle complaints. This can be the same as the other role.`'))
                reply = yield from client.wait_for_message(timeout=30, author=requester, channel=message.channel, check=check)
                if(reply):
                    return reply.role_mentions[0]
                yield from client.send_message(message.channel, '`Timed out`')
                return None
            buffer_min_rank = yield from get_maxmin("lowest")
            buffer_max_rank = yield from get_maxmin("highest")
            yield from client.send_message(message.channel, buffer_min_rank)
            yield from client.send_message(message.channel, buffer_max_rank)
            if(buffer_min_rank and buffer_max_rank):
                min_complaint_role = buffer_min_rank
                max_complaint_role = buffer_max_rank
                yield from dump_config()
            else:
                fail_msg = '`Both a maximum and minimum role must be provided. They are allowed to be the same`'
        else:
            fail_msg = '`Permission Denied`'

    ###### Prune messages ######
    if(yield from command_in_and_useable(['-prune', '-p'], command)):
        if(yield from is_authorised(message.channel.permissions_for(requester).manage_messages, requester)):
            if(len(msgSplit) > 1):
                try:
                    to_purge = min(int(msgSplit[1]) + 1, max_pruned_messages)
                    deleted = yield from client.purge_from(channel=message.channel, limit=to_purge)
                    yield from client.send_message(message.channel, (requester.name + ' deleted {} message(s)').format(len(deleted)))
                except:
                    fail_msg = '`Invalid argument`'
            else:
                fail_msg = '`Argument required`'
        else:
            fail_msg = '`Permission Denied`'

    ###### Toggle self-timeout ######
    if(yield from command_in_and_useable(['-selftimeout', '-sto'], command)):
        if(yield from is_authorised(message.channel.permissions_for(requester).manage_messages, requester)):
            global self_timeout
            self_timeout = not self_timeout
            yield from client.send_message(message.channel, ('`Bot replies will ' + ('now' if self_timeout else 'no longer') + ' be removed after a few seconds`'))
        else:
            fail_msg = '`Permission Denied`'

    ###### Help ######
    if(yield from command_in_and_useable(['-help', '-h'], command)):
        output = "```Commands: \n"
        for key, value in commands_with_help.items():
            output = output + str(key + ". " + value + "\n")
        output = output + "```"
        yield from client.send_message(requester, output)

    ###### Server info ######
    if(yield from command_in_and_useable(['-info', '-i'], command)):
        output = "```###Server Info### \n"
        output = output + (\
                 "Server name: " + str(Server) + "\n"\
                 + "Server region: " + Server.region.name + "\n"\
                 + "Server id: " + str(Server.id) + "\n"\
                 + "Server owner: " + str(Server.owner) + "\n"\
                 + "Created at: " + str(Server.created_at) + "\n"\
                 + "Channel count: " + str(len(Server.channels)) + "\n"\
                 + "Member count: " + str(Server.member_count) + "\n")
        output = output + "```"
        yield from client.send_message(message.channel, output)

    ###### Get selectable role ######
    if(yield from command_in_and_useable(['-getrole', '-gr'], command)):
        if(len(msgSplit) > 1):
            to_add = str(" ".join(msgSplit[1:])).strip("[]'")
            role = yield from is_role(to_add, Server)
            if(role and (role in roles)):
                if(not(discord.utils.get(requester.roles, name=to_add))):
                    yield from discord.Client.add_roles(client, requester, role)
                    yield from client.send_message(message.channel, '`Role acquired`')
                else:
                    fail_msg = '`You already have this role`'
            else:
                fail_msg = '`Invalid role`'
        else:
            fail_msg = '`Argument required`'

    ###### Remove owned selectable role ######
    if(yield from command_in_and_useable(['-removerole', '-rr'], command)):
        if(len(msgSplit) > 1):
            to_rem = str(" ".join(msgSplit[1:])).strip("[]'")
            role = yield from is_role(to_rem, Server)
            if(role and (role in roles)):
                if(discord.utils.get(requester.roles, name=to_rem)):
                    yield from discord.Client.remove_roles(client, requester, role)
                    yield from client.send_message(message.channel, '`Role removed`')
                else:
                    fail_msg = '`You cannot remove a role you do not have`'
            else:
                fail_msg = '`Invalid role`'
        else:
            fail_msg = '`Argument required`'

    ###### Set log channel ######
    if(yield from command_in_and_useable(['-setlogchannel', '-slc'], command)):
        if(yield from is_authorised(requester.server_permissions.administrator, requester)):
            target_channel = message.channel
            yield from client.send_message(message.channel, ('`Set ' + target_channel.name + ' as the log channel? Y/N`'))
            reply = yield from client.wait_for_message(timeout=30, author=requester, channel=target_channel, check=check_yn)
            if(reply):
                global log_channel
                log_channel = (target_channel if reply.content.upper().startswith("Y") else log_channel)
                yield from dump_config()
                yield from client.send_message(message.channel, ('`Log channel {}`'.format(('set to ' + log_channel.name) if reply.content.upper().startswith("Y") else ('unchanged'))))
            else:
                fail_msg = '`Timed out`'
        else:
            fail_msg = '`Permission Denied`'

    ###### Set log channel ######
    #TODO: Refactor this and the above command to remove the copied code
    if(yield from command_in_and_useable(['-setimagechannel', '-sic'], command)):
        if(yield from is_authorised(requester.server_permissions.administrator, requester)):
            target_channel = message.channel
            yield from client.send_message(message.channel, ('`Set ' + target_channel.name + ' as the image channel? Y/N`'))
            reply = yield from client.wait_for_message(timeout=30, author=requester, channel=target_channel, check=check_yn)
            if(reply):
                global image_channel
                image_channel = (target_channel if reply.content.upper().startswith("Y") else image_channel)
                yield from dump_config()
                yield from client.send_message(message.channel, ('`Image channel {}`'.format(('set to ' + image_channel.name) if reply.content.upper().startswith("Y") else ('unchanged'))))
            else:
                fail_msg = '`Timed out`'
        else:
            fail_msg = '`Permission Denied`'

    ###### Set complaint channel ######
    #TODO: Refactor this and the above two commands to remove the copied code
    if(yield from command_in_and_useable(['-setcomplaintchannel', '-scc'], command)):
        if(yield from is_authorised(requester.server_permissions.administrator, requester)):
            target_channel = message.channel
            yield from client.send_message(message.channel, ('`Set ' + target_channel.name + ' as the complaint channel? Y/N`'))
            reply = yield from client.wait_for_message(timeout=30, author=requester, channel=target_channel, check=check_yn)
            if(reply):
                global complaint_channel
                complaint_channel = (target_channel if reply.content.upper().startswith("Y") else complaint_channel)
                yield from dump_config()
                yield from client.send_message(message.channel, ('`Complaint channel {}`'.format(('set to ' + complaint_channel.name) if reply.content.upper().startswith("Y") else ('unchanged'))))
            else:
                fail_msg = '`Timed out`'
        else:
            fail_msg = '`Permission Denied`'

    ###### Changelog ######
    if(yield from command_in_and_useable(['-changelog', '-c'], command)):
        output = "```###Changelog### \n"
        output += "Version " + str(bot_version) + "\n"
        buffer = [str(x) + ". " + str(version_text[x]) + "\n" for x in range(len(version_text))]
        for line in buffer:
            output += str(line)
        output += "```"
        yield from client.send_message(requester, output)

    ###### Make festive ######
    if(yield from command_in_and_useable(['-makefestive', '-ms'], command)):
        if(yield from is_authorised(requester.server_permissions.manage_nicknames, requester)):
            if(Server.me.server_permissions.manage_nicknames):
                mes = yield from client.send_message(message.channel, "`Add a reaction to this message to get a more festive name!`")
                yield from couple_message_and_function(mes, make_festive)
            else:
                fail_msg = '`Bot has insufficient permissions`'
        else:
            fail_msg = '`Permission Denied`'

    ###### Remove festive ######
    if(yield from command_in_and_useable(['-removefestive', '-rs'], command)):
        if(yield from is_authorised(requester.server_permissions.manage_nicknames, requester)):
            if(Server.me.server_permissions.manage_nicknames):
                for member in get_all_members(message.server):
                    buffernick = (member.nick if member.nick else member.name)
                    split_nick = buffernick.split()
                    for emote in festive_emotes:
                        if(emote in split_nick):
                            buffernick = buffernick.strip(festive_emotes)
                            yield from client.change_nickname(user, buffernick)
                            break
            else:
                fail_msg = '`Bot has insufficient permissions`'
        else:
            fail_msg = '`Permission Denied`'
    
    ###### Dump Channel Info ######
    if(yield from command_in_and_useable(['-dumpchannelinfo', '-dci'], command)):
        mes = "```\n"
        mes += message.channel.id + "\n"
        mes += message.channel.server.id + "\n"
        mes +=str(message.channel.position) + "\n"
        mes += "```"
        yield from client.send_message(message.channel, mes)

    ###### Wiki ######
    if(yield from command_in_and_useable(['-wiki', '-w'], command)):
        if(len(msgSplit) > 1):
            for wiki in wikipaths:
                path = get_appended_url(wiki, '_'.join(msgSplit[1:]))
                request = None
                try:
                    request = requests.get(path)
                except:
                    fail_msg = '`Page unavailable`'
                if request.status_code == 200:
                    br = mechanicalsoup.StatefulBrowser()
                    valid = True
                    for disqual in wiki_disqualifiers:
                        br.open(path)
                        page = br.get_current_page()
                        if(disqual in page.title.text):
                            valid = False
                    if(valid):
                        fail_msg = ""
                        yield from client.send_message(message.channel, path)
                        break
                    else:
                        fail_msg = '`Invalid page`'
                else:
                    fail_msg = '`Invalid page`'
        else:
            fail_msg = '`Argument required`'

    ###### Panda ######
    if(yield from command_in_and_useable(['-panda', '-pa'], command)):
        if(message.channel == image_channel or image_channel is None):
            if(len(msgSplit) > 1):
                if(msgSplit[1] == "add"):
                    if(len(msgSplit) > 2):
                        if(msgSplit[2] not in pandas.values()):
                            if('http' in msgSplit[2]):
                                pandas[len(pandas)] = msgSplit[2]
                                yield from dump_pandas()
                                yield from refresh_pandas(message.server)
                                yield from client.send_message(message.channel, '`Added`')
                            else:
                                fail_msg = '`Item must be a link`'
                        else:
                            fail_msg = '`Item already exists`'
                    else:
                        fail_msg = '`Argument required`'
                elif(msgSplit[1] == "del"):
                    if(requester.server_permissions.manage_messages):
                        if(len(msgSplit) > 2):
                            found = False
                            for key, value in pandas.items():
                                if(key == msgSplit[2] or value == msgSplit[2]):
                                    del pandas[key]
                                    yield from dump_pandas()
                                    yield from refresh_pandas(message.server)
                                    yield from client.send_message(message.channel, '`Deleted`')
                                    found = True
                                    break
                            if(not found):
                                fail_msg = '`Item not found`'
                        else:
                            fail_msg = '`Argument required`'
                    else:
                        fail_msg = '`Permission denied`'
            else:
                if(len(pandas) > 0):
                    if(len(pandas) == 1):
                        yield from client.send_message(message.channel, pandas[0])
                    else:
                        random_panda = random.randrange(0, len(pandas))
                        yield from client.send_message(message.channel, pandas[random_panda])
                else:
                    fail_msg = '`Panda list empty`'
        else:
            fail_msg = '`This command must be used in ' + image_channel.name + '`'

                    
                
    
    if(len(fail_msg)):
        yield from client.send_message(message.channel, fail_msg)

###Coupleable functions
@asyncio.coroutine
def make_festive(user):
    if(user):
        buffernick = (user.nick if user.nick else user.name)
        random_emote = str(random.choice(festive_emotes))
        buffernick = random_emote + " " + buffernick +  " " + random_emote
        yield from client.change_nickname(user, buffernick)

def get_key():
    with open(key_file, 'r') as file:
        return str(file.read())
    
boot_attempts = 0
#Do NOT share this key, under any circumstances.
try:
    boot_attempts += 1
    if(boot_attempts == 5):
        print("Possible crash loop detected.")
    client.run(get_key())

except Exception as e:
    error = traceback.format_exc()
    with open(crash_file, "w+") as file:
        file.write(str(error))
        
