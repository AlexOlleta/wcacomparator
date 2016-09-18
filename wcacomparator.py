# -*- coding: utf-8 -*-
"""
Created on Wed Jan 27 12:50:13 2016

@author: Alex
"""

from flask import Flask, render_template, request, Response, url_for, abort, g, \
redirect, flash, session
from json import dumps, loads
import pymysql
import pymysql.cursors

from html import unescape
from lxml import html
import requests
from urllib.request import urlretrieve
from zipfile import ZipFile
from collections import OrderedDict, Counter
from copy import deepcopy

###################################
####  DB Conection and Update  ####
###################################

#Configuration
DEBUG          = True
MYSQL_HOST     = ''
MYSQL_USERNAME = ''
MYSQL_PASSWORD = ''
MYSQL_DATABASE = ''

# Create application
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('prueba_SETTINGS', silent=True)
app.secret_key = ""
medals = {}

# Connect to MySQL.
def connect_db():
    return pymysql.connect(host=app.config['MYSQL_HOST'], user=app.config['MYSQL_USERNAME'], passwd=app.config['MYSQL_PASSWORD'], db=app.config['MYSQL_DATABASE'],charset="utf8")

#####################
####  Functions  ####
#####################
#Events
def wca_events():
    return list(execute('SELECT id, name FROM Events WHERE rank < 900'))
    
def nombre_categoria(categoria):
    return execute("SELECT name FROM Events WHERE id = '{}'".format(categoria),"one")[0]
            
def country_id(WCAid):
    return execute("SELECT countryId FROM Persons WHERE id = '{}'".format(WCAid),"one")[0]
    
def continent_id(WCAid):
    country = country_id(WCAid)
    return execute("SELECT continentId FROM Countries WHERE id = '{}'".format(country),"one")[0]

def continent_country(country):
    return execute("SELECT continentId FROM Countries WHERE id = '{}'".format(country),"one")[0]
    
def gender_id(WCAid):
    return execute("SELECT gender FROM Persons WHERE id = '{}'".format(WCAid),"one")[0]
    
#Gente pais/continente
def people_country(country):
    return [p[0] for p in execute("SELECT id FROM Persons WHERE subid = '1' AND countryId = '{}'".format(country))]

def people_continent(continent):
    return [p[0] for p in execute("SELECT p.id FROM Persons AS p, Countries AS c WHERE p.subid = '1' AND p.countryId = c.id AND c.continentId = '{}'".format(continent))]
    
def isWCAid(arg):
    return not arg.isalpha()
    
#Transformaciones
def times_events(value, measure="time"):
    if value == '' or value is None: return ''
    else:
        if value < -2: return 'error'
        elif value == -1: return 'DNF'
        elif value == -2: return 'DNS'
        elif value == 0: return ''
        if measure == 'number':
            return "{}".format(value)
        if measure == 'time':
            if value < 60 * 100: return "{:.2f}".format(value / 100.0)
            if value < 60 * 60 * 100: return "{}:{:05.2f}".format(value // 6000, value % 6000 / 100.0)
            return "{}:{:02}:{:05.2f}".format(value // 360000, value % 360000 // 6000, value % 6000 / 100.0)
        if measure == 'multi':
            return times_multi(value)
    return 'error'

def times_multi(value):
    # Extract the value parts
    if value >= 1000000000:
        solved = 99 - value // 10000000 % 100
        attempted = value // 100000 % 100
        time = value % 100000
    else:
        difference = 99 - value // 10000000
        time = value // 100 % 100000
        missed = value % 100
        solved = difference + missed
        attempted = solved + missed
    
    # Build the time string
    if time == 99999:
        time = '?:??:??'
    elif time < 60 * 60:
        time = '{}:{:02}'.format(time//60, time%60)
    else:
        time = '{}:{:02}:{:02}'.format(time//3600, time//60%60, time%60)

    #--- Combine.
    return "{}/{} {}".format(solved, attempted, time)

########################
## Información Perfil ##
########################

def records_personales(WCAid):
    resultado = OrderedDict([(event[0],["","",event[1]]) for event in wca_events()])
    for cat in execute("SELECT eventId, best FROM Rankssingle WHERE personId='{}'".format(WCAid)):
        resultado[cat[0]][0] = cat[1]
    for cat2 in execute("SELECT eventId, best FROM Ranksaverage WHERE personId='{}'".format(WCAid)):
        resultado[cat2[0]][1] = cat2[1]
    return resultado
    
def mostrar_rp(WCAid):
    records = records_personales(WCAid)
    for categoria in records.keys():
        if records[categoria][:2] == ["",""]:
            del records[categoria]
    for categoria in records.keys():
        if categoria=="333fm":
            records["333fm"][:2] = [times_events(records["333fm"][0],"number"),times_events(records["333fm"][1])]
        elif categoria=="333mbf":
            records["333mbf"][0] = times_events(records["333mbf"][0],"multi")
        else:
            records[categoria][:2] = [times_events(records[categoria][0]),times_events(records[categoria][1])]
    return records

def comparar_RP_total(WCAid1, WCAid2):
    wcaid1 = records_personales(WCAid1)
    wcaid2 = records_personales(WCAid2)
    resultado = OrderedDict()
    for event in wca_events():
        if event[0] in wcaid1 or event[0] in wcaid2:
            if event in wcaid1:
                resultado.setdefault(event[0],{})["name"] = event[1]
                resultado[event[0]]["single"] = [wcaid1[event[0]][0], ""]
                resultado[event[0]]["average"] = [wcaid1[event[0]][1], ""]
            elif event in wcaid2:
                resultado.setdefault(event[0],{})["name"] = event[1]
                resultado[event[0]]["single"] = ["", wcaid2[event[0]][0]]
                resultado[event[0]]["average"] = ["", wcaid2[event[0]][1]]
            else:  
                resultado.setdefault(event[0],{})["name"] = event[1]
                resultado[event[0]]["single"] = [wcaid1[event[0]][0],wcaid2[event[0]][0]]
                resultado[event[0]]["average"] = [wcaid1[event[0]][1],wcaid2[event[0]][1]]
    return resultado
    
def mostrar_crp_total(WCAid1,WCAid2):
    records = comparar_RP_total(WCAid1,WCAid2)
    for categoria in records.keys():
        if records[categoria]["single"] == ["",""] and records[categoria]["average"] == ["",""]:
            del records[categoria]
    for categoria in records:
        if categoria=="333fm":
            records["333fm"]["single"] = [times_events(records["333fm"]["single"][0],"number"),times_events(records["333fm"]["single"][1],"number")]
            records["333fm"]["average"] = [times_events(records["333fm"]["average"][0]),times_events(records["333fm"]["average"][1])]
        elif categoria=="333mbf":
            records["333mbf"]["single"] = [times_events(records["333mbf"]["single"][0],"multi"),times_events(records["333mbf"]["single"][1],"multi")]
        else:
            records[categoria]["single"] = [times_events(records[categoria]["single"][0]),times_events(records[categoria]["single"][1])]
            records[categoria]["average"] = [times_events(records[categoria]["average"][0]),times_events(records[categoria]["average"][1])]
    return records
    
def evolucion(WCAid, categoria):
    evolution = {"best": [], "average": []}
    for kind in ("best", "average"):
        for tiempo in execute("SELECT competitionId, {0} FROM Results WHERE personId = '{1}' AND eventId = '{2}'".format(kind, WCAid, categoria)):
            if tiempo[1] <= 0 or tiempo[1] == '' or tiempo[1] is None:
                evolution[kind].append("null")
            else:
                if categoria == "333mbf" or (kind == "best" and categoria == "333fm"):
                    evolution[kind].append("{}".format(tiempo[1]))
                else:
                    evolution[kind].append("{:.2f}".format(tiempo[1]/100.0))
        evolution["comps"] = [tiempo[0] for tiempo in resultado]  
        
    evolution["name"] = nombre_categoria(categoria)
    return evolution
        
def medallas(WCAid):
    sql = "SELECT \
    SUM(CASE WHEN results.pos = 1 THEN 1 ELSE 0 END) AS oros, \
    SUM(CASE WHEN results.pos = 2 THEN 1 ELSE 0 END) AS platas, \
    SUM(CASE WHEN results.pos = 3 THEN 1 ELSE 0 END) AS bronces, \
    COUNT(pos) \
    FROM Results \
    WHERE personId ='{}' AND pos < 4 AND (roundId = 'f' OR roundId = 'c') AND best != -1".format(WCAid)
    resultado = execute(sql)
    return {"oros":resultado[0][0],"platas":resultado[0][1],"bronces":resultado[0][2],"total":resultado[0][3]}
    
def comps_years(WCAid):
    return execute("SELECT RIGHT(competitionId, 4) AS year, COUNT(DISTINCT competitionId) FROM Results WHERE personId = '{}' GROUP BY year".format(WCAid))
    
def compsyears(WCAid1, WCAid2):
    compsyear1 = comps_years(WCAid1)
    compsyear2 = comps_years(WCAid2)
    
    min1, min2 = int(compsyear1[0][0]), int(compsyear2[0][0])
    max1, max2 = int(compsyear1[len(compsyear1)-1][0]), int(compsyear2[len(compsyear2)-1][0])

    compsyear = OrderedDict([(str(year), ["",""]) for year in range(min(min1,min2), max(max1, max2) +1)])
    for y1 in compsyear1:
        compsyear[y1[0]][0] = y1[1]
    for y2 in compsyear2:
        compsyear[y2[0]][1] = y2[1]
        
    return compsyear
    
def comps_per_year(pais):
    return execute("SELECT year, COUNT(*) FROM Competitions WHERE countryId = '{}' GROUP BY year".format(pais))
    
#Nemesis
def comparar_RP_comun(WCAid1, WCAid2):
    wcaid1 = records_personales(WCAid1)
    wcaid2 = records_personales(WCAid2)
    resultado = {}
    for event in wca_events():
        if len(wcaid1[event[0]])==2 and len(wcaid2[event[0]])==2:
            resultado[event[0]] = {}
            resultado[event[0]]["single"] = [wcaid1[event[0]][0],wcaid2[event[0]][0]]
            resultado[event[0]]["average"] = [wcaid1[event[0]][1],wcaid2[event[0]][1]]
        elif len(wcaid1[event[0]])==1 and len(wcaid2[event[0]])==1:
            resultado[event[0]] = {}
            resultado[event[0]]["single"] = [wcaid1[event[0]][0],wcaid2[event[0]][0]]
    return resultado
    
def is_nemesis2(WCAid1, WCAid2):
    compar = comparar_RP_comun(WCAid1,WCAid2)
    nemesis = True
    for event in compar:
        for sa in compar[event]:
            if compar[event][sa][1] > compar[event][sa][0]:
                nemesis = False
    return nemesis
    
def people_ranked():
    names, ranks = {}, {}
    for p in execute("SELECT id, name FROM Persons WHERE subid = '1'"):
        names[p[0]] = p[1]
        
    for kind in ("single", "average"):
        for r in execute("SELECT personId, eventId, worldRank FROM Ranks{}".format(kind)):
            ranks.setdefault(r[0], {})[kind+r[1]] = r[2]

    people = sorted(ranks, key=lambda p: (-len(ranks[p]), names[p]))
    return names, ranks, people

def is_nemesis(badguy, victim, ranks):
    badguy_ranks = ranks[badguy]
    for event, rank in ranks[victim].items():
        if event not in badguy_ranks or badguy_ranks[event] >= rank:
            return False
    return True

def nemesis_event(badguy, victim, ranks, radio = 50):
    badguy_ranks = ranks[badguy]
    events = []
    for event, rank in ranks[victim].items():
        if event in badguy_ranks and rank - badguy_ranks[event] <= radio:
            events.append(event)
    return events
    
def my_nemesis(WCAid, names, ranks, people):
    nemeses = {p:{"name":"","events":[]} for p in people if len(ranks[p]) >= len(ranks[WCAid]) and is_nemesis(p, WCAid, ranks)}
    for nem in nemeses.keys():
        nemeses[nem]["events"].append(nemesis_event(nem, WCAid, ranks))
        nemeses[nem]["name"] = names[nem]
    return nemeses
    
def my_nemesis_pc(WCAid, nemesis, people):
    return {w: nemesis[w] for w in nemesis.keys() if w in people}
    
def iam_nemesis(WCAid, ranks, people):
    nemeses = [p for p in people if len(ranks[p]) <= len(ranks[WCAid]) and is_nemesis(WCAid, p, ranks)]
    return nemeses, len(nemeses) 
    
def iam_nemesis_pc(WCAid, nemesis, people):
    return len([w for w in nemesis if w in people])
    
def mostrar_nemesis(mynemesis):
    outnemesis = {person: {"name": mynemesis[person]["name"], \
        "q": len(mynemesis[person]["events"][0]), \
        "events": ", ".join(mynemesis[person]["events"][0])} for person in mynemesis.keys()}
    return OrderedDict(sorted(outnemesis.items(), key=lambda p: -p[1]["q"]))
    
#Records
def number_records(WCAId):
    records = [0, 0, 0]
    sql = "SELECT regionalSingleRecord, regionalAverageRecord FROM Results WHERE personId = '{}' AND (regionalSingleRecord <> '' OR regionalAverageRecord <> '')".format(WCAId)
    for r in execute(sql):
        for s in r:
            if s != '':
                if s == "NR":
                    records[0] += 1
                elif s == "WR":
                    records[2] += 1
                else:
                    records[1] += 1
    records.append(sum(records))
    return records
    
def NRs(pais):
    sql = "SELECT rankssingle.eventId, rankssingle.personId, persons.name, rankssingle.best, ravg.personId, ravg.name, ravg.best FROM Persons,Rankssingle LEFT JOIN \
    (SELECT eventId, personId, persons.name AS name, best FROM Ranksaverage,Persons WHERE countryRank = 1 AND ranksaverage.personId = persons.id AND persons.countryId = '{0}' AND persons.subid = '1') AS ravg \
    ON ravg.eventId = rankssingle.eventId WHERE rankssingle.countryRank = 1 AND rankssingle.personId = persons.id AND persons.countryId = '{0}' AND persons.subid = '1'".format(pais)
    return execute(sql)
    
def mostrar_NRs(country):
    nrs = NRs(country)
    result = []
    for i in range(len(nrs)):
        each = [nrs[i][0],  nrs[i][1], nrs[i][2], "", nrs[i][4], nrs[i][5], ""]
        if nrs[i][0] == "333fm":
            each[3] = times_events(nrs[i][3], "number")
            each[6] = times_events(nrs[i][6], "number")
        elif nrs[i][0] == "333mbf":
            each[3] = times_events(nrs[i][3], "multi")
        else:
            each[3] = times_events(nrs[i][3])
            each[6] = times_events(nrs[i][6])
        result.append(each)
    return result
    
def NRs_compare(pais1, pais2):
    NR1 = NRs(pais1)
    NR2 = NRs(pais2)
    NRsboth = dict.fromkeys(dict(wca_events()), {"single": ["",""], "average": ["",""]})
    for nr1 in NR1:
        if nr1[0] == "333fm":
            NRsboth[nr1[0]]["single"][0] = times_events(nr1[3], "number")
            NRsboth[nr1[0]]["average"][0] = times_events(nr1[6], "number")
        elif nr1[0] == "333mbf":
            NRsboth[nr1[0]]["single"][0] = times_events(nr1[3], "multi")
            NRsboth[nr1[0]]["average"][0] = times_events(nr1[6], "multi")
        else:
            NRsboth[nr1[0]]["single"][0] = times_events(nr1[3])
            NRsboth[nr1[0]]["average"][0] = times_events(nr1[6])
    for nr2 in NR2:
        if nr2[0] == "333fm":
            NRsboth[nr2[0]]["single"][1] = times_events(nr2[3], "number")
            NRsboth[nr2[0]]["average"][1] = times_events(nr2[6], "number") 
        elif nr2[0] == "333mbf":
            NRsboth[nr2[0]]["single"][1] = times_events(nr2[3], "multi")
            NRsboth[nr2[0]]["average"][1] = times_events(nr2[6], "multi") 
        else:
            NRsboth[nr2[0]]["single"][1] = times_events(nr2[3])
            NRsboth[nr2[0]]["average"][1] = times_events(nr2[6])   
    return NRsboth

def mostrar_NRsboth(NRs):
    rest = [e for e in NRs.keys() if NRs[e] == {"single": ["",""], "average": ["",""]}]
    for r in rest:
        del NRs[r]
    return NRs
    
########################    
## Información Paises ##
########################
    
def numero_campeonatos(pais):
    return execute("SELECT COUNT(countryId) FROM Competitions WHERE countryId = '{}'".format(pais),"one")[0]
    
def ncompetidores_año(pais):
    return Counter([y[0] for y in execute("SELECT LEFT(id,4) FROM Persons WHERE CountryId = '{}'".format(pais))])

def ranking_ntop100():
    names, ranks = {}, {}
    for p in execute("SELECT id, name FROM Persons WHERE subid = '1'"):
        names[p[0]] = p[1]
        
    for kind in ("single","average"):
        for r in execute("SELECT personId, eventId, best, worldRank FROM Ranks{} WHERE worldRank < 100".format(kind)):
            ranks.setdefault(r[0], {})[kind+r[1]] = [r[2], r[3]]
    
    people = sorted(ranks, key=lambda p: (-len(ranks[p]), names[p]))
    c = sorted([len(ranks[t]) for t in ranks.keys()], reverse=True) 
    return OrderedDict([(p,{"name":names[p], "events":ranks[p], "pos":c.index(len(ranks[p])) + 1}) for p in people])
    
def ranking_ntop100_pc(ranks, people):
    ranking = deepcopy(ranks)
    rank = OrderedDict([(w, ranking[w]) for w in ranking.keys() if w in people])
    c = sorted([len(rank[t]["events"]) for t in rank.keys()], reverse = True)
    for p in rank.keys():
        rank[p]["pos"] = c.index(len(rank[p]["events"])) + 1
    return rank
    
def mostrar_rntop100(ranking):
    top100 = ranking
    for p in ranking.keys():
        top100[p]["events"] = ", ".join(["{} ({})".format(event, ranking[p]["events"][event][1]) for event in ranking[p]["events"].keys()])
    return top100
    
def numero_top100(pais):
    ntop100 = {}
    for kind in ("single", "average"):
        sql = "SELECT r.eventId, COUNT(countryId) FROM Ranks{} AS r, Persons AS p WHERE p.id = r.personId AND r.worldRank < 100 AND p.countryId = '{}' GROUP BY r.eventId".format(kind, pais)
        ntop100[kind] = {e[0]: e[1] for e in execute(sql)}
    return ntop100
    
def ntop100_pais(ntop100):
    return [len(ntop100["single"]) + len(ntop100["average"]), sum(ntop100["single"].values()) + sum(ntop100["average"].values())]
    
#Medalleros
def medallero():
    sql = "SELECT personId, personName,\
    SUM(CASE WHEN pos = 1 THEN 1 ELSE 0 END) AS oros, \
    SUM(CASE WHEN pos = 2 THEN 1 ELSE 0 END) AS platas, \
    SUM(CASE WHEN pos = 3 THEN 1 ELSE 0 END) AS bronces, \
    COUNT(pos) \
    FROM Results \
    WHERE pos < 4 AND (roundId = 'f' OR roundId = 'c') AND best != -1 \
    GROUP BY personId \
    ORDER BY oros DESC, platas DESC, bronces DESC, personName ASC"
    resultado = execute(sql)
    pos = 1
    rank = OrderedDict([(resultado[0][0], {"name": resultado[0][1], "medals": list(resultado[0][2:5]), "total": resultado[0][5], "pos": 1})])
    for i in range(1,len(resultado)):
        rank[resultado[i][0]] = {"name": resultado[i][1], "medals": list(resultado[i][2:5]), "total": resultado[i][5]}
        if resultado[i][2] == resultado[i-1][2] and resultado[i][3] == resultado[i-1][3] and resultado[i][4] == resultado[i-1][4]:    
            rank[resultado[i][0]]["pos"] = pos
        else:
            rank[resultado[i][0]]["pos"] = i + 1
            pos = i+1
    return rank
    
def medallero_pc(medals, people):
    medallero = deepcopy(medals)
    med = OrderedDict([(w, medallero[w]) for w in medallero.keys() if w in people])
    return ordenar_por_pos(med, "medals")
    
def ordenar_por_pos(dic, var):
    c = sorted([dic[t][var] for t in dic.keys()], reverse=True)
    for p in dic.keys():
        dic[p]["pos"] = c.index(dic[p][var]) + 1
    return dic
    
def medallero_R():
    sql = "SELECT personId, personName, regionalSingleRecord, regionalAverageRecord FROM Results WHERE (regionalSingleRecord <> '' OR regionalAverageRecord <> '')"
    results = execute(sql)
    people = {d[0]:{"name":d[1],"medals":[0,0,0]} for d in results}
    for r in results:
        for s in r[2:]:
            if s != '':
                if s == "NR":
                    people[r[0]]["medals"][0] += 1
                elif s == "WR":
                    people[r[0]]["medals"][2] += 1
                else:
                    people[r[0]]["medals"][1] += 1
    for p in people.keys():
        m = people[p]["medals"]
        people[p]["total"] = m[0] + 5*m[1] + 10*m[2]
    people = ordenar_por_pos(people, "total")
    return OrderedDict(sorted(people.items(), key=lambda r: (-r[1]["total"], r[1]["name"])))
    
def medallero_R_pc(medals, people):
    medallero = deepcopy(medals)
    med = OrderedDict([(w, medallero[w]) for w in medallero if w in people])
    return ordenar_por_pos(med, "total")
    
def number_records_pais(pais):
    records = [0, 0, 0]
    sql = "SELECT regionalSingleRecord, regionalAverageRecord FROM Results WHERE personCountryId = '{}' AND (regionalSingleRecord <> '' OR regionalAverageRecord <> '')".format(pais)
    for r in execute(sql):
        for s in r:
            if s != '':
                if s == "NR":
                    records[0] += 1
                elif s == "WR":
                    records[2] += 1
                else:
                    records[1] += 1
    records.append(records[0] + 5*records[1] + 10*records[2])
    return records
    
def NRs_history(pais):
    sql = "SELECT competitionId, eventId, best, regionalSingleRecord, average, regionalAverageRecord FROM Results WHERE personCountryId = '{}' AND (regionalSingleRecord <> '' OR regionalAverageRecord <> '')".format(pais)
    evolution = {}
    for comp in execute(sql):
        evolution.setdefault(comp[1], {"best": {"comps": [], "data": []}, "average": {"comps": [], "data": []}})
        if comp[3] != '':
            evolution[comp[1]]["best"]["comps"].append(comp[0])
            if comp[1] == "33fm" or comp[1] == "333mbf":
                evolution[comp[1]]["best"]["data"].append("{}".format(comp[2]))
            else:
                evolution[comp[1]]["best"]["data"].append("{:.2f}".format(comp[2]/100.0))
        if comp[5] != '':
            evolution[comp[1]]["average"]["comps"].append(comp[0])
            evolution[comp[1]]["average"]["data"].append("{:.2f}".format(comp[4]/100.0))
    return evolution
    
def porcentaje_sexo(pais):
    sexos = [persona[2] for persona in execute("SELECT id, name, gender FROM Persons WHERE CountryId = '{}'".format(pais))]
    m = sexos.count("m")
    f = sexos.count("f")
    return [("m",m/(m+f)*100),("f",f/(m+f)*100)]
    
    
def sum_of_ranks(pais, n = None):
    people = tuple(people_country(pais))
    total_event = {}
    for kind in ("single", "average"):
        sql1 = "SELECT eventId, COUNT(personId) + 1 FROM Ranks{} WHERE personId in {} GROUP BY eventId".format(kind, people)
        for r in execute(sql1):
            total_event.setdefault(kind, {})[r[0]] = r[1]
      
    ranks = {"single": {p: deepcopy(total_event["single"]) for p in people}, "average": {p: deepcopy(total_event["average"]) for p in people}}
        
    limit = "LIMIT {}".format(1000 + n) if n != None else ''
    for kind in ("single", "average"):
        sql2 = "SELECT personId, eventId, countryRank FROM Ranks{} WHERE personId IN {} ORDER BY countryRank {}".format(kind, people, limit)
        for r in execute(sql2):
            ranks[kind][r[0]][r[1]] = r[2]
            
    rs, ra = ranks["single"], ranks["average"]
            
    sumranks = {v: sum([rs[v][w] for w in rs[v]]) for v in rs.keys()}
    sumranka = {v: sum([ra[v][w] for w in ra[v]]) for v in ra.keys()}
    ordereds = sorted(sumranks.items(), key=lambda x: x[1])
    ordereda = sorted(sumranka.items(), key=lambda x: x[1])
    
    rankings = OrderedDict([(s[0], {"events": rs[s[0]], "total": sumranks[s[0]], "pos":  ordereds.index((s[0],s[1])) + 1}) for s in ordereds])
    rankinga = OrderedDict([(s[0], {"events": ra[s[0]], "total": sumranka[s[0]], "pos":  ordereda.index((s[0],s[1])) + 1}) for s in ordereda])

    return {"single": rankings, "average": rankinga}
    
#print(sum_of_ranks2("Spain", 3))    

def sumofranks_top(sumofrank, n):
    single = OrderedDict(list(sumofrank["single"].items())[:n])
    average = OrderedDict(list(sumofrank["average"].items())[:n])
    return {"single": single, "average": average}
    
#sumofrank = sum_of_ranks2("Spain", 1)
#print(sumofranks_top(sumofrank, 5))
    
def sumofranks_compare(pais1, pais2, n):
    sumofrank = {}
    for pais in (pais1, pais2):
        sfr = sumofranks_top(sum_of_ranks(pais, 1), n)
        for k in ("single", "average"):
            for p in sfr[k].keys():
                sumofrank.setdefault(k, {})[p] = sfr[k][p]
                sumofrank[k][p]["country"] = pais

    ordsing = sorted(sumofrank["single"].items(), key=lambda x: x[1]["pos"])
    ordavg = sorted(sumofrank["average"].items(), key=lambda y: y[1]["pos"])
    return OrderedDict([("single", OrderedDict(ordsing)), ("average", OrderedDict(ordavg))])
    
#####################
## Source's Search ##
#####################
    
def isInLidStats(WCAid, stat):
    page = requests.get("http://hem.bredband.net/_zlv_/rubiks/stats/{}.html".format(stat))
    web = html.fromstring(page.text)
    name = web.xpath('//a[@href="https://www.worldcubeassociation.org/results/p.php?i={}"]/text()'.format(WCAid))
    if len(name) > 0:
        return True
    else:
        return False
         
def links_LidStats(WCAid):
    lids_stats = [["wca_win_events","People that have won in the most WCA events (max=18)"],\
    ["wca_success_events","People that have completed the most WCA events (max=33)"], \
    ["travel_ALL","Most distance traveled"]]
    lids_stats_female = [["female_top20","Female Top 20 lists"],["sum_of_female_ranks","Female Sum of Ranks"]]
    gender = gender_id(WCAid)
    stats = []
    for s in lids_stats:
        if isInLidStats(WCAid, s[0]):
            stats.append(("http://hem.bredband.net/_zlv_/rubiks/stats/{}.html".format(s[0]),s[1]))
    if gender == "f":
        for f in lids_stats_female:
            if isInLidStats(WCAid, f[0]):
                stats.append(("http://hem.bredband.net/_zlv_/rubiks/stats/{}.html".format(f[0]),f[1]))
    return stats

def isInWCAStats(WCAid, stat):
    page = requests.get("https://www.worldcubeassociation.org/results/statistics.php#{}".format(stat))
    web = html.fromstring(page.text)
    name = web.xpath('//div[@id="{}"]//a[@href="/results/p.php?i={}"]/text()'.format(stat,WCAid))
    if len(name) > 0:
        return True
    else:
        return False    

def links_WCAStats(WCAid):
    WCA_stats = [["medal_collection","Best \"medal collection\" (3x3x3 and overall)"],\
    ["sum_ranks_345","Sum of 3x3/4x4/5x5 ranks (Single | Average)"],\
    ["sum_ranks_single","Sum of all single ranks"],\
    ["sum_ranks_average","Sum of all average ranks"],\
    ["appearances_top100_3x3","Appearances in Rubik's Cube top 100 results (Single | Average)"],\
    ["subx_3x3_solves","Most Sub-X solves in Rubik's Cube"],\
    ["blind_streak_3x3","Rubik's Cube Blindfolded longest success streak"],\
    ["blind_success_rate","Rubik's Cube Blindfolded recent success rate (since Jun 10, 2015 - minimum 5 attempts)"],\
    ["wrs_in_most_events","World records in most events (current and past)"],\
    ["podiums_3x3","Best Podiums in Rubik's Cube event"],\
    ["oldest_world_records","Oldest standing world records"],\
    ["most_persons","Most Persons"],\
    ["most_competitions","Most Competitions"],\
    ["most_countries","Most Countries"],\
    ["most_solves","Most solves in one competition or year"]]
    return [("https://www.worldcubeassociation.org/results/statistics.php#{}".format(s[0]),s[1]) for s in WCA_stats if isInWCAStats(WCAid, s[0])]
    
def isIniWCAStats(WCAid, stat="prize|rank", kind="single", region="World", gender="0"):
    page = requests.get("http://iwca.jp/ranking/{1}?region={2}&gender={3}&misc={0}&{1}=".format(stat, kind, region, gender))
    web = html.fromstring(page.text)
    name = web.xpath('//a[@href="/person/detail/id/{}"]/text()'.format(WCAid))
    if len(name) > 0:
        return True
    else:
        return False
        
def links_iWCAStats(WCAid):
    country = country_id(WCAid)
    gender = gender_id(WCAid)
    continente = continent_id(WCAid)[1:]
    stats = []
    for r in (country, continente, "World"):
        if isIniWCAStats(WCAid, stat="prize", region=r):
            text = "Weighted medals table in {}".format(r)
            stats.append(("http://iwca.jp/ranking/single?region={}&gender=0&misc=prize&single=".format(r), text))
            break
    for k in ("single", "average"):
        for r in (country, continente, "World"):
            if isIniWCAStats(WCAid, stat="rank", kind=k, region=r):
                text = "Sum of Ranks in {} ({})".format(r, k)
                stats.append(("http://iwca.jp/ranking/{0}?region={1}&gender=0&misc=rank&{0}=".format(k, r), text))
                break
    if gender == "f":
        for r in (country, continente, "World"):
            if isIniWCAStats(WCAid, stat="prize", region=r):
                text = "Weighted medals table in {} [Female]".format(r)
                stats.append(("http://iwca.jp/ranking/single?region={}&gender=Female&misc=prize&single=".format(r), text))
                break
        for k in ("single", "average"):
            for r in (country, continente, "World"):
                if isIniWCAStats(WCAid, stat="rank", kind=k, region=r, gender="Female"):
                    text = "Sum of Ranks in {} ({}) [Female]".format(r, k)
                    stats.append(("http://iwca.jp/ranking/{0}?region={1}&gender=Female&misc=rank&{0}=".format(k, r), text))
                    break
    return stats
    
def isInWCADbStats(WCAid, stat="kinchranks|awecc", region="World", gender="all", show="100"):
    kinch = "?region={}&gender={}&show={}".format(region, gender, show) if stat == "kinchranks" else ""
    page = requests.get("http://wcadb.net/{}.php{}".format(stat, kinch))
    web = html.fromstring(page.text)
    name = web.xpath('//a[@href="person.php?id={}"]/text()'.format(WCAid))
    if len(name) > 0:
        return True
    else:
        return False
        
def links_WCADbStats(WCAid):
    country = country_id(WCAid)
    gender = gender_id(WCAid)
    continente = continent_id(WCAid)[1:]
    stats = []
    if isInWCADbStats(WCAid, stat="awecc"):
        stats.append(("http://wcadb.net/awecc.php", "\"All WCA Events Completion\" Club"))
    for r in (country, continente, "World"):
        for s in ("100", "1000"):
            if isInWCADbStats(WCAid, stat="kinchranks", region=r, show=s):
                text = "Kinchranks of {} ({} people)".format(r, s)
                stats.append(("http://wcadb.net/kinchranks.php?region={}&gender=all&show={}".format(r, s), text))
                break
    if gender == "f":
        for r in (country, continente, "World"):
            for s in ("100", "1000"):
                if isInWCADbStats(WCAid, stat="kinchranks", region=r, gender="female", show=s):
                    text = "Kinchranks of {} ({} people) [Female]".format(r, s)
                    stats.append(("http://wcadb.net/kinchranks.php?region={}&gender=female&show={}".format(r, s), text))
                    break
    else:
        for r in (country, continente, "World"):
            for s in ("100", "1000"):
                if isInWCADbStats(WCAid, stat="kinchranks", region=r, gender="male", show=s):
                    text = "Kinchranks of {} ({} people) [Male]".format(r, s)
                    stats.append(("http://wcadb.net/kinchranks.php?region={}&gender=male&show={}".format(r, s), text))
                    break
    return stats
    
def links_sources(WCAid):
    lid = links_LidStats(WCAid)
    wca = links_WCAStats(WCAid)
    iwca = links_iWCAStats(WCAid)
    wcadb = links_WCADbStats(WCAid)
    links = OrderedDict()
    if len(lid) > 0:
        links["lid"] = {"name": "Lid's WCA Stats", "links":lid}
    if len(wca) > 0:
        links["wca"] = {"name": "WCA's Official Stats", "links":wca}
    if len(iwca) > 0:
        links["iwca"] = {"name": "iWCA's Stats", "links":iwca}
    if len(wcadb) > 0:
        links["wcadb"] = {"name": "WCA Database's Stats", "links":wcadb}
    return links
    
def links_intersection(WCAid1, WCAid2):
    lid = list(set(links_LidStats(WCAid1)) & set(links_LidStats(WCAid2)))
    wca = list(set(links_WCAStats(WCAid1)) & set(links_WCAStats(WCAid2)))
    iwca = list(set(links_iWCAStats(WCAid1)) & set(links_iWCAStats(WCAid2)))
    wcadb = list(set(links_WCADbStats(WCAid1)) & set(links_WCADbStats(WCAid2)))
    links = OrderedDict()
    if len(lid) > 0:
        links["lid"] = {"name": "Lid's WCA Stats", "links":lid}
    if len(wca) > 0:
        links["wca"] = {"name": "WCA's Official Stats", "links":wca}
    if len(iwca) > 0:
        links["iwca"] = {"name": "iWCA's Stats", "links":iwca}
    if len(wcadb) > 0:
        links["wcadb"] = {"name": "WCA Database's Stats", "links":wcadb}
    return links
        
############
## Extras ##
############
        
def enviar(nombre,email, mensaje):
    pass

def volver():
    pass

def execute(sql, fetch = "all"):
    cursor = g.connection.cursor()
    cursor.execute(sql)
    if fetch == "one":
        return cursor.fetchone()
    return cursor.fetchall()

#Pruebas
def prueba_sql(sql):
    cursor = g.connection.cursor()
    cursor.execute(sql)
    return cursor.fetchall()
    
def descargar_wcadb_sql():
#    import os
    page = requests.get('https://www.worldcubeassociation.org/results/misc/export.html')
    web = html.fromstring(page.text)
    sqlfile = web.xpath('//dt/a/text()')[0]
    url = "https://www.worldcubeassociation.org/results/misc/{}".format(sqlfile)

    file_name = "WCA_DB.sql.zip"
    file_dir = "database"
    
    urlretrieve(url,file_name)
    with ZipFile(file_name,'r') as file:
        file.extract("WCA_export.sql",file_dir)
        
def archivos_json():
    try:
        with open("names.json","r") as n:
            names = loads(n.read())
        with open("ranks.json","r") as r:
            ranks = loads(r.read())
        with open("people.json","r") as l:
            people = loads(l.read())
        return names, ranks, people
    except:
        names, ranks, p = people_ranked()
        with open("names.json","w") as n:
            n.write(dumps(names))
        with open("ranks.json","w") as r:
            r.write(dumps(ranks))
        with open("people.json","w") as l:
            l.write(dumps(p))
        return {}, {}, {}
        
###########################
####  Page's Requests  ####
###########################

@app.before_request
def before_request():
    g.connection = connect_db()
    
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route("/")
def index():
    names, ranks, p = archivos_json()
    global medals
    medals = medallero()
    return render_template("index.html", error="", find=unescape("Find &raquo;"), compare=unescape("Compare &raquo;"))

@app.route("/find", methods=['GET'])
#@app.route("/ver.html", methods=["GET"])
def find():
    names, ranks, p = archivos_json()
    medals = medallero()
    
    if 'id' not in request.args or request.args["id"] == "":
        return render_template("find.html")
#    elif request.args["id"] != "" and not isWCAid(request.args["id"]):
#        abort(400)
    elif isWCAid(request.args["id"]):    
        WCAid = request.args["id"]
        try:
            country = country_id(WCAid)
        except TypeError:
            return render_template("index.html", error="*Wrong WCA ID", find=unescape("Find &raquo;"), compare=unescape("Compare &raquo;"))
            
        people_cy = people_country(country)
        continent = continent_country(country)
        people_ct = people_continent(continent)
        
        medals_cy = medallero_pc(medals, people_cy)
        medals_ct = medallero_pc(medals, people_ct)
        
#        global names, ranks, p
        mynemesis = my_nemesis(WCAid, names, ranks, p)
        nemesisof, qnf = iam_nemesis(WCAid, ranks, p)
        
        cys = comps_years(WCAid)
        
        return render_template("find_wca.html", find="Find", \
        params=dict(wcaid=WCAid, fullname=names[WCAid],\
        ncomps= sum([c[1] for c in cys]), compsyear = cys, \
        nrecords = number_records(WCAid), medallas = medallas(WCAid),\
        medallasr = [medals_cy[WCAid]["pos"], medals_ct[WCAid]["pos"], medals[WCAid]["pos"]], \
        nemesis = mostrar_nemesis(mynemesis), \
        lnemesis = qnf, \
#        sources = links_sources(request.args["id"]), \
        records = mostrar_rp(request.args["id"])))
    else:
        country = request.args["id"]
        people_cy = people_country(country)
        if len(people_cy) == 0:
            return render_template("index.html", error = "*Wrong Country", find=unescape("Find &raquo;"), compare=unescape("Compare &raquo;"))
            
        medalleror = medallero_R()
        top100r = ranking_ntop100()
        
        return render_template("find_country.html", find="Find", params=dict(fullname=country,\
        ncomps = numero_campeonatos(country), medallas = medallero_pc(medals, people_cy), \
        nrs = mostrar_NRs(country), rank_record = medallero_R_pc(medalleror, people_cy), \
        top100 = mostrar_rntop100(ranking_ntop100_pc(top100r, people_cy))))
    
@app.route("/query_json.json", methods=['GET'])
def query_json():
    if 'q' not in request.args:
        return Response(render_template('query_json.json', params=dict(result="", json="")), mimetype="application/json")
    else:
        q = prueba_sql(request.args["q"])
        lengths = [0] * len(q[0])
        for i in range(len(q)):
            for j in range(len(q[0])):
                if len(str(q[i][j])) > lengths[j]:
                    lengths[j] = len(str(q[i][j]))
        
        t = request.args["t"].split(",")
        tit = []
        for k in range(len(t)):
            tit.append("{:<{}}".format(t[k], lengths[k] + 5))
        l = []
        for i in range(len(q)):
            row = []
            for j in range(len(q[0])):
                row.append("{:<{}}".format(q[i][j], lengths[j] + 5))
            l.append("".join(row))
        return Response(render_template('query_json.json', params=dict(result=dumps("".join(tit)),json=dumps(l))), mimetype="application/json")

@app.route("/chart_json.json", methods=["GET"])
def chart_json():
    if 'cat2' not in request.args:
        if isWCAid(request.args["id1"]):
            times = evolucion(request.args["id1"], request.args["cat1"])
            yaxis = times["comps"]
            return Response(render_template('chart_json.json', params=dict(evo=times, n1=yaxis, n2=yaxis)), mimetype="application/json")
        else:
            times = NRs_history(request.args["id1"])[request.args["cat1"]]
            return Response(render_template('chart_json.json', params=dict(evo=times)), mimetype="application/json")
    else:
        return Response(render_template("chart_json.json"), mimetype="application/json")
    
@app.route("/compare", methods=['GET'])
def compare():
#    if request.args["categoria"] not in wca_events():
#        abort(400)
#    else:
#        return render_template("comparar.html", params="3x3x3")
    if 'id1' not in request.args or 'id2' not in request.args:
        return render_template("compare.html")
    elif isWCAid(request.args["id1"]) and isWCAid(request.args["id2"]):
        global medals, names, ranks, p
        if len(medals) == 0:
            medals = medallero()
        names, ranks, p = people_ranked()
            
        WCAid1, WCAid2 = request.args["id1"], request.args["id2"]
        
        try:
            country1 = country_id(WCAid1)
        except TypeError:
            return render_template("index.html", error="*Wrong left WCA ID", find=unescape("Find &raquo;"), compare=unescape("Compare &raquo;"))
        try:
            country2 = country_id(WCAid2)
        except TypeError:
            return render_template("index.html", error="*Wrong rigth WCA ID", find=unescape("Find &raquo;"), compare=unescape("Compare &raquo;"))
        
        medalleroR = medallero_R()
#        global medals
                        
        if country1 == country2:
            continent1 = continent2 = continent_country(country1)
            people_cy1 = people_cy2 = people_country(country1)
            people_ct1 = people_ct2 = people_continent(continent1)
            medalleroRcy1 = medalleroRcy2 = medallero_R_pc(medalleroR, people_cy1)
            medalleroRct1 = medalleroRct2 = medallero_R_pc(medalleroR, people_ct1)
            medalscy1 = medalscy2 = medallero_pc(medals, people_cy1)
            medalsct1 = medalsct2 = medallero_pc(medals, people_ct1)
        else:
            continent1, continent2 = continent_country(country1), continent_country(country2)
            people_cy1, people_cy2 = people_country(country1), people_country(country2)
            people_ct1, people_ct2 = people_continent(continent1), people_continent(continent2)
            medalleroRcy1 = medallero_R_pc(medalleroR, people_cy1)
            medalleroRcy2 = medallero_R_pc(medalleroR, people_cy2)
            medalleroRct1 = medallero_R_pc(medalleroR, people_ct1)
            medalleroRct2 = medallero_R_pc(medalleroR, people_ct2)
            medalscy1 = medallero_pc(medals, people_cy1)
            medalscy2 = medallero_pc(medals, people_cy2)
            medalsct1 = medallero_pc(medals, people_ct1)
            medalsct2 = medallero_pc(medals, people_ct2)
                            
        compsyear1, compsyear2 = comps_years(WCAid1), comps_years(WCAid2)
        compsyear = compsyears(WCAid1, WCAid2)
            
#        global names, ranks, p
        cnemesisof1, lcn1 = iam_nemesis(WCAid1, ranks, p)
        cnemesisof2, lcn2 = iam_nemesis(WCAid2, ranks, p)
        cnemesisofpais1 = iam_nemesis_pc(WCAid1, cnemesisof1, people_cy1)
        cnemesisofpais2 = iam_nemesis_pc(WCAid2, cnemesisof2, people_cy2)
        cnemesisofcont1 = iam_nemesis_pc(WCAid1, cnemesisof1, people_ct1)
        cnemesisofcont2 = iam_nemesis_pc(WCAid2, cnemesisof2, people_ct2)
        
        cmynemesis1 = my_nemesis(WCAid1, names, ranks, p)
        cmynemesis2 = my_nemesis(WCAid2, names, ranks, p)
        cnemesispais1 = my_nemesis_pc(WCAid1, cmynemesis1, people_cy1)
        cnemesispais2 = my_nemesis_pc(WCAid2, cmynemesis2, people_cy2)
        cnemesiscont1 = my_nemesis_pc(WCAid1, cmynemesis1, people_ct1)
        cnemesiscont2 = my_nemesis_pc(WCAid2, cmynemesis2, people_ct2)
        
        return render_template("compare_wca.html", compare="Compare", \
        wcaid1 = WCAid1, wcaid2 = WCAid2, \
        params=dict(isnemesis=is_nemesis2(WCAid1,WCAid2),\
        fullname1=names[WCAid1],fullname2=names[WCAid2],\
        ncomps1=sum([c[1] for c in compsyear1]),ncomps2=sum([c[1] for c in compsyear2]),\
        medallas1=medallas(WCAid1),medallas2=medallas(WCAid2), \
        nempais1 = len(cnemesispais1), nempais2 = len(cnemesispais2), \
        nemcont1 = len(cnemesiscont1), nemcont2 = len(cnemesiscont2), \
        nemworld1 = len(cmynemesis1), nemworld2 = len(cmynemesis2), \
        nemofpais1 = cnemesisofpais1, nemofpais2 = cnemesisofpais2, \
        nemofcont1 = cnemesisofcont1, nemofcont2 = cnemesisofcont2, \
        nemofworld1 = lcn1, nemofworld2 = lcn2, compsyears = compsyear, \
        rank_record1 = medalleroRcy1, rank_record2 = medalleroRcy2, \
        records_cont1 = medalleroRct1, records_cont2 = medalleroRct2, \
        rankrecord_world = medalleroR, medalswr = medals, \
        medalsn1 = medalscy1, medalsn2 = medalscy2, \
        medalsc1 = medalsct1, medalsc2 = medalsct2, \
#        sources = links_intersection(WCAid1, WCAid2), \
        records=mostrar_crp_total(WCAid1,WCAid2)))
    else:
        country1, country2 = request.args["id1"], request.args["id2"]
        
        nc1 = comps_per_year(country1)
        nc2 = comps_per_year(country2)
        if len(nc1) == 0:
            return render_template("index.html", error = "*Wrong left Country", find=unescape("Find &raquo;"), compare=unescape("Compare &raquo;"))
        elif len(nc2) == 0:
            return render_template("index.html", error = "*Wrong right Country", find=unescape("Find &raquo;"), compare=unescape("Compare &raquo;"))
        
        mf1 = porcentaje_sexo(country1)
        mf2 = porcentaje_sexo(country2)
        ncs1 = ncompetidores_año(country1)
        ncs2 = ncompetidores_año(country2)
        sumncomps1 = sum([ncs1[c] for c in ncs1.keys()])
        sumncomps2 = sum([ncs2[c] for c in ncs2.keys()])
    
        return render_template("compare_country.html", \
        params=dict(fullname1 = country1, fullname2 = country2, compare="Compare", \
        eventss = ["333","444","555", "222","333bf","333oh","333fm","333ft","minx","pyram","sq1","clock","skewb","666","777","444bf","555bf","333mbf"], \
        eventsa = ["333","444","555", "222","333bf","333oh","333fm","333ft","minx","pyram","sq1","clock","skewb","666","777"], \
        records = mostrar_NRsboth(NRs_compare(country1, country2)), \
        sumofrank = sumofranks_compare(country1, country2, 3), \
        ncwrecs1 = number_records_pais(country1), ncwrecs2 = number_records_pais(country2), \
        ncomps1 = sum([m[1] for m in nc1]), ncomps2 = sum([m[1] for m in nc2]), \
        meancy1 = "{0:.2f}".format(sum([m[1] for m in nc1])/len(nc1)), meancy2 = "{0:.2f}".format(sum([m[1] for m in nc2])/len(nc2)), \
        malefemale1 = "{0:.2f}% / {1:.2f}%".format(mf1[0][1], mf1[1][1]), malefemale2 = "{0:.2f}% / {1:.2f}%".format(mf2[0][1], mf2[1][1]), \
        top1001 = ntop100_pais(numero_top100(country1)), top1002 = ntop100_pais(numero_top100(country2)), \
        ncompetidores1 = sumncomps1, ncompetidores2 = sumncomps2, \
        meancty1 = "{0:.2f}".format(sumncomps1/len(ncs1)), meancty2 = "{0:.2f}".format(sumncomps2/len(ncs2))))
    
@app.route("/links",methods=['GET'])
def links():
    return render_template("links.html")
    
@app.route("/query",methods=['GET'])
def query():
    if 'q' not in request.args:
        return render_template("query.html", params="Algo no ha ido bien.")
    else:
        sql = "SELECT * FROM event"
        return render_template("query.html", params=prueba_sql(sql))
    
@app.route("/query_more", methods=["GET"])
def query_more():
    return render_template("query_more.html")

if __name__ == "__main__":
    app.run()