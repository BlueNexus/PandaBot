import discord
import asyncio
import math

log_file = "log.txt"
client = discord.Client()
roles = []
protected_roles = []
commands = {'>addselrole':True, '>removeselrole':True, '>getrole':True, '>removerole':True, '>listroles':True, '>help':True, '>prune':True, '>protectrole':True}
commands_with_help = {'>addselrole [role]':'Adds a role to the list of publically available roles', \
                      '>removeselrole [role]':'Removes a role from the list of publically available roles', \
                      '>getrole [role]':'Acquire the specified role from the list of publically available roles', \
                      '>removerole [role]':'Removes the specified publically available role from your account', \
                      '>listroles':'Lists all publically available roles', \
                      '>prune [limit]':'(Moderation) Deletes the last [limit] messages, where limit is a number.', \
                      '>protectrole [role][1/0]':'(Administration) Adds or removes a role to/from the list of protected roles, which cannot be made publically available.'}
short_commands = {'>asr':True, '>rsr':True, '>gr':True, '>rr':True, '>lr':True, '>h':True, '>p':True, '>pr':True}
linked_commands = {'>addselrole':'>asr', '>removeselrole':'>rsr', '>getrole':'>gr', '>removerole':'>rr', '>listroles':'>lr', '>help':'>h', '>prune':'>p', '>protectrole':'>pr'}
known_servers = []

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

@client.event
@asyncio.coroutine
def on_member_join(member):
    yield from client.send_message(member.server.default_channel, ('` ' + member.name + ' has joined the server.`'))

@client.event
@asyncio.coroutine
def on_member_remove(member):
    yield from client.send_message(member.server.default_channel, ('` ' + member.name + ' has left the server.`'))

@client.event
@asyncio.coroutine
def on_message(message):
    if((message.server not in known_servers) and message.server is not None):
        yield from refresh_roles(message.server)
        known_servers.append(message.server)
    if message.content.startswith('>'):
        yield from print_to_log(message)
        message_split = message.content.split()
        if((message_split[0] in commands) or (message_split[0] in short_commands)):
            yield from handle_command(message, message_split[0])
        else:
            yield from client.send_message(message.channel, '`Command not found`')

@asyncio.coroutine
def is_role(msg, Ser):
    return(discord.utils.get(Ser.roles, name=msg))

@asyncio.coroutine
def dump_roles():
    with open("roles.txt", "w+") as file:
        for role in roles:
            file.write(role.name + "\n")
        for pro_role in protected_roles:
            file.write("### " + pro_role.name + "\n")
    print("Done.")

@asyncio.coroutine
def print_to_log(message):
    with open(log_file, "a") as file:
        file.write(str(message.timestamp) + " " + str(message.author) + " " + message.clean_content + "\n")

@asyncio.coroutine
def refresh_roles(server):
    if(server not in known_servers):
        print("Loading roles for " + server.name)
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
    if(yield from command_in_and_useable(['>addselrole', '>asr'], command)):
        if(requester.server_permissions.manage_roles):
            if(len(msgSplit) > 1):
                to_add = msgSplit[1]
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
    if(yield from command_in_and_useable(['>removeselrole', '>rsr'], command)):
        if(requester.server_permissions.manage_roles):
            if(len(msgSplit) > 1):
                to_rem = msgSplit[1]
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
    if(yield from command_in_and_useable(['>listroles', '>lr'], command)):
        output = "```Selectable roles: \n"
        for role_no, role in enumerate(roles):
            output = output + str(str(role_no + 1) + ". " + role.name + "\n")
        output = output + "```"
        yield from client.send_message(message.channel, output)

    ###### Manage protected roles ######
    if(yield from command_in_and_useable(['>protectrole', '>pr'], command)):
        if(requester.server_permissions.administrator):
            if(len(msgSplit) > 2):
                role = yield from is_role(msgSplit[1], Server)
                if(role):
                    if(role < requester.top_role):
                        if((int(msgSplit[2]) == 1) and role not in protected_roles):
                            protected_roles.append(role)
                            yield from dump_roles()
                            yield from client.send_message(message.channel, '`Role ' + role.name + ' protected`')
                        elif((int(msgSplit[2]) == 0) and role in protected_roles):
                            protected_roles.remove(role)
                            yield from dump_roles()
                            yield from client.send_message(message.channel, '`Role ' + role.name + ' unprotected`')
                        elif(int(msgSplit[2]) not in [1, 2]):
                             failmsg = '`Invalid argument. Expecting either 1 or 2`'
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
    if(yield from command_in_and_useable(['>prune', '>p'], command)):
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

    ###### Help ######
    if(yield from command_in_and_useable(['>help', '>h'], command)):
        output = "```Commands: \n"
        for key, value in commands_with_help.items():
            output = output + str(key + ". " + value + "\n")
        output = output + "```"
        yield from client.send_message(requester, output)


    ###### Get selectable role ######
    if(yield from command_in_and_useable(['>getrole', '>gr'], command)):
        if(len(msgSplit) > 1):
            to_add = msgSplit[1]
            role = yield from is_role(to_add, Server)
            if(role and (role in roles)):
                if(not(discord.utils.get(requester.roles, name=to_add))):
                    if(role < requester.top_role):
                        yield from discord.Client.add_roles(client, requester, role)
                        yield from client.send_message(message.channel, '`Role acquired`')
                    else:
                        fail_msg = '`Permission Denied`'
                else:
                    fail_msg = '`You already have this role`'
            else:
                fail_msg = '`Invalid role`'
        else:
            fail_msg = '`Argument required`'

    ###### Remove owned selectable role ######
    if(yield from command_in_and_useable(['>removerole', '>rr'], command)):
        if(len(msgSplit) > 1):
            to_rem = msgSplit[1]
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
    
    if(len(fail_msg)):
        yield from client.send_message(message.channel, fail_msg)

client.run('tokengoeshere')
