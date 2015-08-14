#!/usr/bin/python
# -*- coding: utf-8 -*-

import bugzilla
import datetime
from fedora.client import AuthError, AccountSystem
import getpass

DAYS_AGO = 365
client = AccountSystem()
bz = bugzilla.Bugzilla(url='https://bugzilla.redhat.com/xmlrpc.cgi')

def process_user(username):
    fas_user = client.person_by_username(username)
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
                                print(u"{0} <{1}> is a good guy - worked on BZ {2}".format(human_name, username, bug.id))
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
                                print(u"{0} <{1}> is a good guy - removed FE-NEEDSPONSOR from BZ {2}".format(human_name, username, bug.id))
                                break # no need to check rest of bug
                        else:
                            continue # hack to break to outer for-loop if we called break 2 lines above
                        break
    if not good_guy:
        print(u"{0} <{1}> done no sponsor work".format(human_name, username))


#client.username = "msuchy"
#client.password = "XXXX"

try:
    sponsors = client.group_members("packager")
except AuthError as e:
    client.username = raw_input('Username: ').strip()
    client.password = getpass.getpass('Password: ')
    sponsors = client.group_members("packager")

sponsors = [s.username for s in sponsors if s.role_type == "sponsor"]

for sponsor in sponsors:
    process_user(sponsor)
