import discord
import asyncio
import math
import time
import datetime
#
######## CONFIG ########
config_file = "config.txt"
log_file = "log.txt"
roles_file = "roles.txt"
self_timeout = False
########################

####### GLOBALS ########
client = discord.Client()
roles = []
protected_roles = []
log_channel = None
meeting_channel = None
minutes = []

########################

commands = {'-addselrole':True, '-removeselrole':True, '-getrole':True, '-removerole':True, '-listroles':True, '-help':True, '-prune':True, '-protectrole':True, '-info':True, '-selftimeout':True, '-setlogchannel':True}
commands_with_help = {'-addselrole [role]':'Adds a role to the list of publically available roles', \
                      '-removeselrole [role]':'Removes a role from the list of publically available roles', \
                      '-getrole [role]':'Acquire the specified role from the list of publically available roles', \
                      '-removerole [role]':'Removes the specified publically available role from your account', \
                      '-info':'Shows information about the current server', \
                      '-listroles':'Lists all publically available roles', \
                      '-prune [limit]':'(Moderation) Deletes the last [limit] messages, where limit is a number.', \
                      '-protectrole [role][1/0]':'(Administration) Adds or removes a role to/from the list of protected roles, which cannot be made publically available.', \
                      '-selftimeout':'Toggles whether or not bot messages will be removed after a few seconds', \
                      '-setlogchannel':'Sets the current channel as the designated "log" channel, where deleted messages etc. will be logged.'}
short_commands = {'-asr':True, '-rsr':True, '-gr':True, '-rr':True, '-lr':True, '-h':True, '-p':True, '-pr':True, '-i':True, '-sto':True, '-slc':True}
linked_commands = {'-addselrole':'-asr', '-removeselrole':'-rsr', '-getrole':'-gr', '-removerole':'-rr', '-listroles':'-lr', '-help':'-h', '-prune':'-p', '-protectrole':'-pr', '-info':'-i', '-selftimeout':'-sto', '-setlogchannel':'-slc'}
known_servers = []

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

@client.event
@asyncio.coroutine
def on_member_join(member):
    '''
    params: member (Member object)
    returns: None
    Announces that a new member has joined the server, in the server's default channel.
    '''
    yield from client.send_message(member.server.default_channel, ('` ' + member.name + ' has joined the server.`'))

@client.event
@asyncio.coroutine
def on_member_remove(member):
    '''
    params: member (Member object)
    returns: None
    Announces that a member has left the server, in the server's default channel.
    '''
    yield from client.send_message(member.server.default_channel, ('` ' + member.name + ' has left the server.`'))

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
        known_servers.append(message.server)
    #If it's a command
    if message.content.startswith('-'):
        yield from message_to_log(message)
        message_split = message.content.split()
        if((message_split[0] in commands) or (message_split[0] in short_commands)):
            yield from handle_command(message, message_split[0])
        else:
            yield from client.send_message(message.channel, '`Command not found`')
    #If it's from the bot, and timeout is enabled, delete the message.
    if((message.author.id == client.user.id) and self_timeout):
        time.sleep(5)
        yield from client.delete_message(message)

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
    with open(config_file, "w+") as file:
        if(log_channel is not None):
            file.write("# " + log_channel.id + "\n")
        if(len(minutes)):
            for item in minutes:
                file.write("@" + str(item) + "\n")
    yield from event_to_log("Done.")

@asyncio.coroutine
def event_to_log(message):
    with open(log_file, "a") as file:
        file.write("\n" + str(datetime.datetime.now()) + " " + message)

#Deprecated
@asyncio.coroutine
def message_to_log(message):
    with open(log_file, "a") as file:
        file.write(str(message.timestamp) + " " + str(message.author) + " " + message.clean_content + "\n")

@asyncio.coroutine
def refresh_roles(server):
    if(server not in known_servers):
        yield from event_to_log("Loading roles for " + server.name)
        with open("roles.txt", "r") as file:
            lines = [line.rstrip('\n') for line in file]
            for line in lines:
                if(line.startswith("###")):
                    line = line.split()
                    cur_role = yield from is_role(line[1], server)
                    if(cur_role):
                        protected_roles.append(cur_role)
                    continue
                cur_role = yield from is_role(line, server)
                if(cur_role):
                    roles.append(cur_role)

@asyncio.coroutine
def refresh_config(server):
    if(server not in known_servers):
        yield from event_to_log("Loading config for " + server.name)
        global minutes
        global log_channel
        minutes = []
        with open(config_file, "r") as file:
            lines = [line.rstrip('\n') for line in file]
            for line in lines:
                split_line = line.split()
                if(line.startswith("#")):
                    log_channel = server.get_channel(split_line[1])
                if(line.startswith("@")):
                    minutes.append(split_line[1])
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

@asyncio.coroutine
def handle_command(message, command):
    Server = message.server
    fail_msg = ""
    requester = message.author #yield from discord.Server.get_member_named(discord.Server, name = message.author)
    msgSplit = message.content.split()
    
    ###### Add selectable role ######
    if(yield from command_in_and_useable(['-addselrole', '-asr'], command)):
        if(requester.server_permissions.manage_roles):
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
        if(requester.server_permissions.manage_roles):
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
        if(requester.server_permissions.administrator):
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
                        

    ###### Prune messages ######
    if(yield from command_in_and_useable(['-prune', '-p'], command)):
        if(message.channel.permissions_for(requester).manage_messages):
            if(len(msgSplit) > 1):
                try:
                    to_purge = int(msgSplit[1])
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
        if(message.channel.permissions_for(requester).manage_messages):
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
        if(requester.server_permissions.administrator):
            target_channel = message.channel

            def check(msg):
                if(msg.content.startswith("Y") or msg.content.startswith("N")):
                    return True
                return False

            yield from client.send_message(message.channel, ('`Set ' + target_channel.name + ' as the log channel? Y/N`'))
            reply = yield from client.wait_for_message(timeout=30, author=requester, channel=target_channel, check=check)
            if(reply):
                global log_channel
                log_channel = (target_channel if reply.content.upper().startswith("Y") else log_channel)
                yield from dump_config()
                yield from client.send_message(message.channel, ('`Log channel {}`'.format(('set to ' + log_channel.name) if reply.content.upper().startswith("Y") else ('unchanged'))))
            else:
                fail_msg = '`Timed out`'
        else:
            fail_msg = '`Permission Denied`'
            
                

                
        
    
    if(len(fail_msg)):
        yield from client.send_message(message.channel, fail_msg)

#Do NOT share this key, under any circumstances. 
client.run()
