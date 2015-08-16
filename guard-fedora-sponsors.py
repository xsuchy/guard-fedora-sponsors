#!/usr/bin/python
# -*- coding: utf-8 -*-

import bugzilla
import datetime
from fedora.client import AuthError, AccountSystem
import getpass

DAYS_AGO = 365
client = AccountSystem()
bz = bugzilla.Bugzilla(url='https://bugzilla.redhat.com/xmlrpc.cgi')

# cache mapping of user id to name
map_id_to_name = {}
def convert_id_to_name(user_id):
    if user_id not in map_id_to_name:
        map_id_to_name[user_id] = client.person_by_id(user_id).username
    return map_id_to_name[user_id]

def process_user(username):
    fas_user = client.person_by_username(username)
    if fas_user.status != u'active':
        return None
    human_name = bz.getuser(fas_user.bugzilla_email).real_name
    good_guy = False
    #bz.url_to_query("https://bugzilla.redhat.com/buglist.cgi?chfield=bug_status&chfieldfrom=2014-08-13&chfieldto=Now&classification=Fedora&component=Package%20Review&email1=msuchy%40redhat.com&emailassigned_to1=1&emailtype1=substring&list_id=3718380&product=Fedora&query_format=advanced")
    bugs = bz.query({'query_format': 'advanced',
        'component': 'Package Review', 'classification': 'Fedora', 'product': 'Fedora',
        'emailtype1': 'substring', 'email1': fas_user.bugzilla_email, 'emailassigned_to1': '1',
        'list_id': '3718380', 'chfieldto': 'Now', 'chfieldfrom': '-{0}d'.format(DAYS_AGO),
        'chfield': 'bug_status'})
    for bug in bugs:
        history = bug.get_history()
        # 177841 is FE-NEEDSPONSOR
        if 177841 in bug.blocks:
            # check if sponsor changed status of the bug
            for change in history['bugs'][0]['history']:
                if change['when'] > datetime.date.today() - datetime.timedelta(DAYS_AGO):
                    if change['who'] == human_name:
                        for i in change['changes']:
                            if 'field_name' in i:
                                good_guy = True
                                print(u"{0} <{1}> worked on BZ {2}".format(human_name, username, bug.id))
                                break # no need to check rest of bug
                        else:
                            continue # hack to break to outer for-loop if we called break 2 lines above
                        break

        else:
            # check if sponsor removed FE-NEEDSPONSOR in past one year
            for change in history['bugs'][0]['history']:
                if change['when'] > datetime.date.today() - datetime.timedelta(DAYS_AGO):
                    if change['who'] == human_name:
                        for i in change['changes']:
                            if 'removed' in i and 'field_name' in i and \
			    i['removed'] == '177841' and i['field_name'] == 'blocks':
                                good_guy = True
                                print(u"{0} <{1}> removed FE-NEEDSPONSOR from BZ {2}".format(human_name, username, bug.id))
                                break # no need to check rest of bug
                        else:
                            continue # hack to break to outer for-loop if we called break 2 lines above
                        break

    if fas_user.id in DIRECTLY_SPONSORED:
        good_guy = True
        sponsored_users = DIRECTLY_SPONSORED[fas_user.id]
        sponsored_users = [convert_id_to_name(u) for u in sponsored_users]
        print(u"{0} <{1}> - directly sponsored: {2}".format(human_name, username, sponsored_users))

    if not good_guy:
        print(u"{0} <{1}> - no recent sponsor activity".format(human_name, username))


#client.username = "msuchy"
#client.password = "XXXX"

try:
    packagers = client.group_members("packager")
except AuthError as e:
    client.username = raw_input('Username: ').strip()
    client.password = getpass.getpass('Password: ')
    packagers = client.group_members("packager")

sponsors = [s.username for s in packagers if s.role_type == "sponsor"]
packagers = [p.username for p in packagers]
packager_group = client.group_by_name("packager")

DIRECTLY_SPONSORED = {}
for role in packager_group.approved_roles:
    if role.role_type == u'user':
        approved_date = datetime.datetime.strptime(role.approval, '%Y-%m-%d %H:%M:%S.%f+00:00')
        if approved_date > datetime.datetime.today() - datetime.timedelta(DAYS_AGO):
            if role.sponsor_id in DIRECTLY_SPONSORED:
                DIRECTLY_SPONSORED[role.sponsor_id].extend([role.person_id])
            else:
                DIRECTLY_SPONSORED[role.sponsor_id] = [role.person_id]

for sponsor in sponsors:
    process_user(sponsor)
