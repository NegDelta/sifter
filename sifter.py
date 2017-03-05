from __future__ import print_function
import sys
import requests
import json

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

accountid = ''
entrylist = []
cardlist = []

usage = (
    'sifter.py: Determines most valuable SIF cards in your deck using a' +
    ' School Idol\nTomodachi account.\n' +
    'usage: sifter.py [-a | -s acc_id | output_path [acc_id]]\n' +
    '    -a    Return SIT account ID currently stored in config file.\n' +
    '    -s    Store new SIT account ID in config file.\n' +
    '\n' +
    'Returns a semicolon-separated CSV file.\n' +
    'Selected for keeping are top 9 cards by score in each attribute:\n' +
    '    overall,\n' +
    '    with Healer and Perfect Lock skills,\n' +
    '    of each of 3 µ\'s sub-units,\n' +
    'and all non-µ\'s cards.\n'
    'Card score takes into account the kizuna bonus.\n' +
    'It is assumed that ane Rare cards can/will be idolized.'
)

# TODO: rewrite to argparse
if len(sys.argv) < 2:
    print(usage)
    sys.exit()
elif sys.argv[1] == '-a':
    conffile = open('sifter.conf')
    print(conffile.read())
    sys.exit()
elif sys.argv[1] == '-s':
    if len(sys.argv) < 3:
        sys.exit('Account ID not specified')
    else:
        conffile = open('sifter.conf','w')
        conffile.write(sys.argv[2])
        sys.exit()
else:
    if len(sys.argv) < 3:
        conffile = open('sifter.conf')
        accountid = conffile.read()
    else:
        accountid = sys.argv[2]
    
# and finally, do the actual stuff this bunch of code is supposed to do

outfile = open(sys.argv[1], 'w')

qurl = ('http://schoolido.lu/api/ownedcards/?'+
    'owner_account='+str(accountid)+'&stored=Deck&card__is_special=False')

while True:
    r = requests.get(qurl)
    result = r.json()['results']
    entrylist += [[i['card'],i['idolized']] for i in result]
    eprint('Got {}/{} results'.format(
        len(entrylist),
        r.json()['count'] )   
    )
    if r.json()['next'] == None:
        break
    qurl = r.json()['next']
    
kizunabonus = {
    'URi': 1000,
    'UR':   500,
    'SSRi': 750,
    'SSR':  375,
    'SRi':  500,
    'SR':   250,
    'Ri':   200,
    'R':    200,
    'Ni':    50,
    'N':     50,
}
attr = ['smile','pure','cool']
musubs = ['Bibi','Printemps','Lily White']

for card in entrylist:
    idol = requests.get(
        'http://schoolido.lu/api/cards/{}/'.format(card[0])
    ).json()
    
    idol['image'] = idol['card'+'_idolized'*card[1]+'_image']
    
    mu_bonus = 1.0
    aq_bonus = 1.0
    if idol['idol']['main_unit'][1:3] == "'s":
        mu_bonus = 1.1
    if idol['idol']['main_unit'] == "Aqours":
        aq_bonus = 1.1
        
    if card[1]: #idolized
        idol['rarity'] += 'i'
        
    for a in attr:
        idol['maxstats_'+a] = idol[
            'non_'*(not card[1]) + 'idolized_maximum_statistics_' + a
        ]  
          
    idol['maxstats_' + idol['attribute'].lower()] += (
        kizunabonus[idol['rarity']]
    )
    
    for a in attr:
        idol['maxstats_'+a+'_mu'] = int(idol['maxstats_'+a] * mu_bonus)
        idol['maxstats_'+a+'_aq'] = int(idol['maxstats_'+a] * aq_bonus)

    #charm=score, trick=pl, yell=heal
    idol['skillgroup'] = ''
    if idol['skill'] != None:
        if idol['skill'] == 'Healer' or (
            idol['skill'][-4:] == 'Yell'):
            idol['skillgroup'] = 'Healer'
        elif idol['skill'] == 'Perfect Lock' or (
            idol['skill'][-5:] == 'Trick'):
            idol['skillgroup'] = 'Perf Lock'
        elif idol['skill'] == 'Score Up' or (
            idol['skill'][-5:] == 'Charm'):
            idol['skillgroup'] = 'Score'
    
    idol['merits'] = ''
    
    cardlist += [idol]
    eprint('Got {}/{} card data'.format(
        len(cardlist),
        len(entrylist) )   
    )

for a in attr:
    #general top9
    for idol in sorted(cardlist, key=lambda d: d['maxstats_'+a])[-9:]:
        idol['merits'] += 'Gen '+a+'/'
    #sub-unit top9
    for sub in musubs:
        for idol in sorted(
            [card for card in cardlist if card['idol']['sub_unit'] == sub], 
            key=lambda i: i['maxstats_'+a]
        )[-9:]:
            idol['merits'] += sub+' '+a+'/'
    #healer/pl top9
    for sub in ['Healer','Perf Lock']:
        for idol in sorted(
            [card for card in cardlist if card['skillgroup'] == sub], 
            key=lambda i: i['maxstats_'+a]
        )[-9:]:
            idol['merits'] += sub+' '+a+'/'

fields = ['RARITY','COLLECTION','NAME','SUB','ATTR',
      'SMILE',  'PURE',  'COOL',
    'M-SMILE','M-PURE','M-COOL',
    'A-SMILE','A-PURE','A-COOL',
    'SKILL','MERITS','IMAGE']

outfile.write(';'.join(fields)+'\n')
for idol in cardlist:
    outfile.write((('{};'*len(fields))[:-1]+'\n').format(
        idol['rarity'],
        idol['translated_collection'],
        idol['idol']['name'],
        idol['idol']['sub_unit'],
        idol['attribute'],
        idol['maxstats_smile'],
        idol['maxstats_pure'],
        idol['maxstats_cool'],
        idol['maxstats_smile_mu'],
        idol['maxstats_pure_mu'],
        idol['maxstats_cool_mu'],
        idol['maxstats_smile_aq'],
        idol['maxstats_pure_aq'],
        idol['maxstats_cool_aq'],
        idol['skillgroup'],
        idol['merits'][:-1],
        'http:' + idol['image'],
    ))
