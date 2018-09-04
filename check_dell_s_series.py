#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Nagios check plugin for Dell | EMC² S-series switches, running OS10 firmware
   This check retrieve operational values from Dell specific SNMP MIBs :
   - hardware health
   - power unit status
   - fans status
   - temperatures
   For switching specific metrics (interface stats, etc) it uses standard NET-SNMP MIBs, so
   you can use generic SNMP check as the excellent check_nwc_health from Consol Labs:
   https://labs.consol.de/nagios/check_nwc_health/
   2018-09-04 - Eric Belhomme <rico-github@ricozome.net>
"""
from __future__ import print_function

import commands
import sys
import optparse
import re
import os
import netsnmp

__author__ = 'Eric Belhomme'
__contact__ = 'rico-github@ricozome.net'
__version__ = '0.1'
__license__ = 'MIT'

nagiosStatus = {
	'0': 'OK',
	'1': 'WARNING',
	'2': 'CRITICAL',
	'3': 'UNKNOWN'
}

Os10CmnOperStatus = {
	'1': 'up',
	'2': 'down',
	'3': 'testing',
	'4': 'unknown',
	'5': 'dormant',
	'6': 'notPresent',
	'7': 'lowerLayerDown',
	'8': 'failed'
}

Os10ChassisDefType = {
	'1': 's6000on',
	'2': 's4048on',
	'3': 's4048Ton',
	'4': 's3048on',
	'5': 's6010on',
	'6': 's4148Fon',
	'7': 's4128Fon',
	'8': 's4148Ton',
	'9': 's4128Ton',
	'10': 's4148FEon',
	'11': 's4148Uon',
	'12': 's4200on',
	'13': 'mx5108Non',
	'14': 'mx9116Non',
	'15': 's5148Fon',
	'16': 'z9100on',
	'17': 's4248FBon',
	'18': 's4248FBLon',
	'19': 's4112Fon',
	'20': 's4112Ton',
	'21': 'z9264Fon',
	'9999': 'unknown'
}

Os10CardOperStatus = {
	'1': 'ready',
	'2': 'cardMisMatch',
	'3': 'cardProblem',
	'4': 'diagMode',
	'5': 'cardAbsent',
	'6': 'offline'
}

def getSnmpOperStatus(snmpOID, textval, warn, crit):
	message = []
	retCode = 0
	countfail =0
	var = netsnmp.VarList(netsnmp.Varbind(snmpOID))
	vals = snmpSession.walk(var)
	if vals:
		index = 1
		for item in vals:
			if int(item) == 4:
				retCode = 3
#				message.append(textval + ' number '+ index + 'repported as ' + Os10CmnOperStatus.get(item))
			else:
				if int(item) != 1:
					countfail += 1
#					message.append(textval + ' number '+ index + 'repported as ' + Os10CmnOperStatus.get(item))
			message.append(textval + ' number '+ str(index) + ' reported as ' + Os10CmnOperStatus.get(item))
			index += 1

		if retCode != 3:
			if countfail == 0:
				retCode = 0
				message.insert(0,'all ' + textval + '(s) OK')
			else:
				message.insert(0,'failed or error found for ' + textval)
				if countfail < warn:
					retCode = 1
				if countfail < crit:
					retCode = 2
	else:
		retCode = 3
		message.insert(0, 'Unable to get SNMP metrics from server !')

	print( nagiosStatus.get(str(retCode)), ': ', end='' )
	for item in message:
		print( item)
	print('')
	return retCode

def getSystemInfo():
	message = []
	retCode = 0
	cardStatus = 6
	vars = netsnmp.VarList(
		netsnmp.Varbind('.1.3.6.1.2.1.1.5', 0), # sysName
		netsnmp.Varbind('.1.3.6.1.2.1.1.2', 0), # sysObjectId
		netsnmp.Varbind('.1.3.6.1.2.1.1.1', 0)) # sysDescr
	vals = snmpSession.get(vars)
	if vals:
		message.append(vals[0] + ' (' + vals[1] + ' - ' + vals[2] + ')')
	else:
		retCode = 3
		message.insert(0, 'Unable to get SNMP metrics from server !')

	vars = netsnmp.VarList(
		netsnmp.Varbind('.1.3.6.1.4.1.674.11000.5000.100.4.1.1.3.1.2'), # chassis type
		netsnmp.Varbind('.1.3.6.1.4.1.674.11000.5000.100.4.1.1.3.1.6'), # chassis hw rev.
		netsnmp.Varbind('.1.3.6.1.4.1.674.11000.5000.100.4.1.1.3.1.4'), # chassis p/n
		netsnmp.Varbind('.1.3.6.1.4.1.674.11000.5000.100.4.1.1.3.1.7')) #chassis service tag
	vals = snmpSession.get(vars)
	if vals:
		message.append('chassis: ' + Os10ChassisDefType.get(vals[0]) + ' (rev. ' + vals[1] + ') - p/n:' + vals[2] + ' - ServiceTag:' + vals[3])
	else:
		retCode = 3
		message.insert(0, 'Unable to get SNMP metrics from server !')

	vars = netsnmp.VarList(
		netsnmp.Varbind('.1.3.6.1.4.1.674.11000.5000.100.4.1.1.4.1.3'), # card descr
		netsnmp.Varbind('.1.3.6.1.4.1.674.11000.5000.100.4.1.1.4.1.8'), # card h/w rev.
		netsnmp.Varbind('.1.3.6.1.4.1.674.11000.5000.100.4.1.1.4.1.6'), # card P/N
		netsnmp.Varbind('.1.3.6.1.4.1.674.11000.5000.100.4.1.1.4.1.4'), # card status
		netsnmp.Varbind('.1.3.6.1.4.1.674.11000.5000.100.4.1.1.4.1.9')) # card Service Tag
	vals = snmpSession.get(vars)
	if vals:
		cardStatus = int(vals[3])
		message.append('card: ' + vals[0] + ' (rev. ' + vals[1] + ') - p/n:' + vals[2] + ' - ServiceTag:' + vals[4] + ' - status:' + Os10CardOperStatus.get(vals[3]))
	else:
		retCode = 3
		message.insert(0, 'Unable to get SNMP metrics from server !')

	if cardStatus != 1:
		if (cardStatus == 4 or cardStatus == 6) and retCode < 1:
			retCode = 1
		else:
			retCode = 2

	print(nagiosStatus.get(str(retCode)) + ':', end=' ')
	for item in message:
		print( item)
	return retCode

def getTemperatures(warn, crit):
	retCode = 0
	message = []
	vars = netsnmp.VarList(
		netsnmp.Varbind('.1.3.6.1.4.1.674.11000.5000.100.4.1.1.3.1.11'), # chassis temp.
		netsnmp.Varbind('.1.3.6.1.4.1.674.11000.5000.100.4.1.1.4.1.5'))  # card temp.
	vals = snmpSession.walk(vars)
	if vals:
		for temp in vals:
			if int(temp) > int(crit) and retCode < 2:
				retCode = 2
				message.append('temperature sensor at ' + temp + ' °C exceed critical threshold (' + str(crit) + '°C)')
			elif int(temp) > int(warn) and retCode < 1:
				retCode = 1
				message.append('temperature sensor at ' + temp + ' °C exceed warning threshold (' + str(warn) + '°C)')
			else:
				message.append('temperature sensor at ' + temp + ' °C')
	else:
		retCode = 3
		message.insert(0, 'Unable to get SNMP metrics from server !')	
	if retCode == 0:
		avg = sum(map(int, vals)) / len(vals)
		message.insert(0, 'all temperature sensors OK with an average of '+ str(avg) + '°C')

	print(nagiosStatus.get(str(retCode)) + ':', end=' ')
	for item in message:
		print( item)
	return retCode

def getArgs():
	host=''
	community=''
	mode=''
	warn=0
	crit=0
	usage = "usage: %prog -H <host> -C <community> -m ( fans | power | health | temp ) [ -w <warn>  ] [ -c crit ]"
	descr = 'Nagios check plugin for Dell|EMC S-series switches running OS10 firmware'
	epilog = __author__ + ' <' + __contact__ + '> - ' + __license__ + ' license'
	optp = optparse.OptionParser(usage=usage, version="%prog " + __version__, description=descr, epilog=epilog)
	optp.add_option('-H', '--host', help='IP address', dest='host')
	optp.add_option('-C', '--community', help='SNMPv2 community', dest='community')
	optp.add_option('-m', '--mode', help='mode (fans | power | health | temp)', dest='mode')
	optp.add_option('-w', '--warning', help='warning threshold', dest='warning')
	optp.add_option('-c', '--critical', help='critical threshold', dest='critical')
	opts, args = optp.parse_args()

	if opts.host is None:
		print('Error: missing IP address')
		optp.print_help()
		sys.exit(1)
	else:
		host = opts.host

	if opts.mode is None:
		print('Error: missing mode')
		optp.print_help()
		sys.exit(1)
	else:
		pattern = re.compile('^(fans|power|health|temp)$')
		if not pattern.match(opts.mode):
			print('Error: unknown mode \'' + opts.mode + '\'')
			optp.print_help()
			sys.exit(1)
		else:
			mode = opts.mode

	if opts.community is None:
		community = 'public'
	else:
		community = opts.community

	if opts.warning is None:
		if mode == 'fans':
			warn = 1
		if mode == 'power':
			warn = 0
		if mode == 'temp':
			warn = 50
	else:
		warn = opts.warning
		
	if opts.critical is None:
		if mode == 'fans':
			crit = 2
		if mode == 'power':
			crit = 1
		if mode == 'temp':
			crit = 60
	else:
		crit = opts.critical

	return host, community, mode, warn, crit
	

if __name__ == '__main__':
	retCode = 3
	host, community, mode, warn, crit = getArgs()
	snmpSession = netsnmp.Session( Version = 2, DestHost=host, Community=community )

	if mode == 'fans':
		# os10FanTrayOperStatus MIB
		retCode = getSnmpOperStatus('.1.3.6.1.4.1.674.11000.5000.100.4.1.2.2.1.4', 'fan', warn, crit)
	if mode == 'power':
		# os10PowerSupplyOperStatus MIB
		retCode = getSnmpOperStatus('.1.3.6.1.4.1.674.11000.5000.100.4.1.2.1.1.4', 'PSU', warn, crit)
	if mode == 'temp':
		retCode = getTemperatures(warn, crit)
	if mode == 'health':
		retCode = getSystemInfo()

	sys.exit(retCode)