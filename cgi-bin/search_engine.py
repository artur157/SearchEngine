#!/usr/bin/env python3
#*- coding: utf-8 -*-
#  форма для поисковика

import cgi
import html
import sqlite3
import cgitb; cgitb.enable()

import requests
from requests.exceptions import ConnectionError
import os
import sys
import json
from queue import Queue
from hashlib import sha256
from urllib.parse import urljoin, urlparse
#from lxml.html import etree
#from lxml.etree import XMLSyntaxError
import time
import logging
from pprint import pprint

import requests
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch

import pymorphy2
from gensim.models import Word2Vec, Doc2Vec
import nltk
import nltk.data
from nltk.corpus import stopwords


def ceil(x):
    return int(x) if int(x) == x else int(x)+1


def connect_elasticsearch():
    _es = None
    _es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
    #if not _es.ping():
    #    print('Awww it could not connect!')
    return _es


def search(es_object, index_name, search_object):
    res = es_object.search(index=index_name, body=search_object)
    return res


def get_term_suggest_string(query):
    return  {'suggest': {
                 'suggestion': {
                     'text': query,
                     "term": {
                         "field": "suggestion"
                     }
                 }
            }
        }

def get_phrase_suggest_string(query):   # не используется
    return  {'suggest': {
                 'suggestion': {
                     'text': query,
                     'phrase': {
                         'field': 'suggestion',
                         'size': 1,
                         'collate': {
                             'query': {
                                 'inline': {
                                     'match_phrase': {
                                         'suggestion.bigrammed': '{{suggestion}}'
                                     }
                                 }
                             }
                         },
                         "max_errors": 2
                     }
                 }
            }
        }

def get_query_string(query):
    return  {"_source": ["title", "url", "body_vector"],
             'query':
                 {'multi_match':
                      {'query': query,
                       'fields': ['title^2', 'body', 'url^5', 'title.bigrammed^10','body.bigrammed^5'],
                       #'analyzer': 'default',
                       'tie_breaker': 0.7}},
             'highlight': {
                 'fields': {
                     'body': {
                         'fragment_size': 100,
                         'number_of_fragments': 3,
                         'no_match_size': 200
                     }
                 },
                 'pre_tags': ['<em class="hlt1">'],
                 'post_tags': ['</em>'],
             },
             'from': page_num * 10}


def get_script_query_string(query):
    zero_vector = []
    for i in range(300):
        zero_vector.append(0)

    query_vector = get_query_vector(query)
    if sum(query_vector) == 0:
        return get_query_string(query)

    return {"_source": ["title", "url", "body_vector"],
            "query": {
    "script_score": {
        "query": {"match_all": {}},
        "script": {
            "source": "l1norm(params.zero_vector, doc['body_vector']) == 0 ? 0 : cosineSimilarity(params.query_vector, doc['body_vector']) + 1.0",
            "params": {"query_vector": query_vector,
                       "zero_vector": zero_vector}
        }
    }
    },
        'from': page_num * 10}


def get_bool_query_string(query):
    zero_vector = []
    for i in range(300):
        zero_vector.append(0)

    query_vector = get_query_vector(query)
    if sum(query_vector) == 0:
        return get_query_string(query)

    return  {"_source": ["title", "url", "body_vector"],
             'query': {
                 "bool": {
                 "should": {
                        'multi_match': {
                           'query': query,
                           'fields': ['title^2', 'body', 'url^5', 'title.bigrammed^10','body.bigrammed^5'],
                           'analyzer': 'default',
                           'tie_breaker': 0.7,
                            'boost': 0.15}},
                     "must": {
            "script_score": {
                "query": {"match_all": {}},
                "script": {
                    "source": "l1norm(params.zero_vector, doc['body_vector']) == 0 ? 0 : cosineSimilarity(params.query_vector, doc['body_vector']) + 1.0",
                    "params": {"query_vector": query_vector,
                               "zero_vector": zero_vector}
                }}}}},
             'highlight': {
                 'fields': {
                     'body': {
                         'fragment_size': 100,
                         'number_of_fragments': 3,
                         'no_match_size': 200
                     }
                 },
                 'pre_tags': ['<em class="hlt1">'],
                 'post_tags': ['</em>'],
             },
             'from': page_num * 10}


def get_query_vector(query):
    # загружаем модель
    model = Word2Vec.load("F:\\my_word2vec_1")   # ОБРАТИ ВНИМАНИЕ !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    result_vector = []
    for i in range(300):
        result_vector.append(0)

    word_list = senttolist(query, True)    # False для doc2vec   # ОБРАТИ ВНИМАНИЕ !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    word_list_len = len(word_list)

    # прибавить result_vector к model[word]
    if word_list_len > 0:
                                               # ОБРАТИ ВНИМАНИЕ !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        for word in word_list:
            try:
                word_vector = model[word]
                for i in range(300):
                    result_vector[i] += word_vector[i]
            except Exception as ex:
                #print(word,'not found in vocabulary')
                j = 0

        for i in range(300):
            result_vector[i] /= word_list_len
        '''
        try:
            result_vector = model.infer_vector(word_list).tolist()
        except Exception as ex:
            #print('infer trouble')
            j = 0
        '''


    return result_vector


def senttolist(sent, rmv_stop):
    #global stop_words, morph
    w_list = nltk.word_tokenize(sent, language="russian")
    w_list = [morph.parse(word.lower())[0].normal_form for word in w_list if word.isalpha()]
    if rmv_stop:
        w_list_without_stops = [w for w in w_list if not w in stop_words]   # удалить из word_list стоп-слова
        return w_list_without_stops
    return w_list


if __name__ == '__main__':

    # получаем переданные методом GET значения
    form = cgi.FieldStorage()
    query = html.escape(form.getvalue("query", ""))
    page_num = int(form.getvalue("page", 0))
    stop_words = set(stopwords.words('russian'))
    morph = pymorphy2.MorphAnalyzer()

    # выводим общие элементы
    print("Content-type: text/html\n")
    #print("charset: utf-8\n")
    print("""<!DOCTYPE HTML>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <link rel="stylesheet" href="../css/searchEngineStyle.css" type="text/css">
                    </head>
                    <script src="../scripts/showSuggestAsync.js"></script>
                    <body>
                        <form class="form-flex" action="search_engine.py">
                            <img src="../img/kubsu_magnifier.png" alt="" width="120">&nbsp &nbsp &nbsp &nbsp 
                            <input type="text" name="query" id="query-field" autocomplete="off" size="70px" value="{0}" oninput="showSuggestAsync();" onclick="showSuggestAsync();"><input type="submit" name="submit" value="" id="submit">
                        </form>
                         <div id="complete-list"></div>
                         <br> <br> <br>
                         <span class="main-span">
                        <div class="page">
                    """.format(query))

    if query != "":
        es = connect_elasticsearch()
        morph = pymorphy2.MorphAnalyzer()

        if es is not None:                        # russian !!!! ПОМОГЛО  но my_analyzer...
            # ЕСЛИ НАДО, ИСПРАВЛЯЕМ ТЕРМ ОПЕЧАТКИ
            search_object = get_term_suggest_string(query)
            answer = search(es, 'kubsu1', json.dumps(search_object))

            query_term_corrected = query    # будем исправлять в нем терм ошибки

            for suggestion in answer['suggest']['suggestion']:
                if len(suggestion['options']) > 0:
                    wrong_word = suggestion['text']
                    right_word = suggestion['options'][0]['text']
                    query_term_corrected = query_term_corrected.replace(wrong_word, right_word)

            if query != query_term_corrected:
                # заново ищем, уже по исправленному запросу
                print('<div class="stroka_tolko">Исправлена опечатка "<em class="hlt1">' + query + '</em>"</div><br>')




            search_object = get_query_string(query_term_corrected)    # теперь основной поиск по (возможно, исправленному) запросу
            answer = search(es, 'kubsu1', json.dumps(search_object))

            results = int(answer['hits']['total']['value'])     # сколько найдено результатов

            if results > 0:

                print('<div class="stroka_tolko">Найдено {0} результатов</div><br>'.format(results))

                MAX_PAGE_NUM = ceil(results / 10) - 1

                print("<ol>")
                #lines = []   # УБРАТЬ!

                order_num = 1

                for result in answer['hits']['hits']:
                    #print(result['_score'])
                    snippet = ""
                    try:
                        snippet = " ... ".join(result['highlight']['body'])    # формируем аннотации
                    except:
                        u = 0

                    print('<li class="separated"> <h3><a href="{0}" onclick="showSimilarDocs({4},{3})" target="_blank">{1}</a></h3> <div class="green"><p class="clip"><a href="{0}" '
                          'onclick="showSimilarDocs({4},{3})" target="_blank">{0}</a></p></div> <br> <div id="div{4}">{2}</div> </li><br>'.format(
                        result['_source']['url'],
                        result['_source']['title'],
                        snippet,
                        result['_source']['body_vector'],
                        order_num))


                    order_num += 1
                    #lines.append(result['_source']['url']+'&'+result['_source']['title']) # УБРАТЬ!


                with open("M:\\бо_dm_h.txt", "a", encoding='utf-8') as file: # УБРАТЬ!
                    #file.write('$'.join(lines)+'$') # УБРАТЬ!
                    kk=0
                print("</ol>")

                # тут надо сделать номера страниц в виде ссылок
                if MAX_PAGE_NUM > 0:
                    print('&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;')
                    left_range = 0 if page_num < 4 else MAX_PAGE_NUM-4 if page_num == MAX_PAGE_NUM else page_num-3
                    right_range = MAX_PAGE_NUM if MAX_PAGE_NUM < 4 else left_range + 4
                    if left_range != 0:
                        print('<FONT size="+2"><a href="search_engine.py?query={0}&page=0">В начало</a></FONT>&nbsp;&nbsp;&nbsp;'.format(query_term_corrected))
                    for i in range(left_range, right_range + 1):
                        if i == page_num:
                            print('<FONT size="+2"><span class="page-num-chosen">{2}</span></FONT>&nbsp;&nbsp;&nbsp;'.format(query, i, i + 1))
                        else:
                            print('<FONT size="+2"><a href="search_engine.py?query={0}&page={1}"><span class="page-num">{2}</span></a></FONT>&nbsp;&nbsp;&nbsp;'.format(query_term_corrected, i, i + 1))
                    if page_num != MAX_PAGE_NUM:
                        print('<FONT size="+2"><a href="search_engine.py?query={0}&page={1}">Следующая</a></FONT>'.format(query_term_corrected, page_num + 1))

                    print('<br><br><br>')

            else:
                print('<div class="stroka_tolko">По запросу <b>{0}</b> ничего не найдено.</div>'.format(query))
        else:
            print('<div class="stroka_tolko">Отсутствует соединение с сервером.</div>')
    else:
        print('<div class="stroka_tolko">Задан пустой поисковый запрос.</div>')

    print(""" </div> <div class="facets"><div><fieldset class="fieldset-auto-width"><div class="faset-cap">Тип поиска</div><div class="fieldset-content">
    <li class="box-group"><input type="radio" name="search-type" value="normal" id="normal" class="bigbox" checked="checked" /><label for="normal" class="label">Обычный</label></li>
    <li class="box-group"><input type="radio" name="search-type" value="concept" id="concept" class="bigbox" /><label for="concept" class="label">Концептуальный</label></li>
    </div></fieldset></div><br> <div><fieldset class="fieldset-auto-width"><div class="faset-cap">Где искать</div><div class="fieldset-content">
    
    <li class="box-group"><input type="radio" name="faset" value="all" id="all" class="bigbox" onclick="checkRadio(0);" checked="checked" /><label for="all" class="label">Везде</label></li>
    <li class="box-group"><input type="radio" name="faset" value="category" id="category" class="bigbox" onclick="checkRadio(1);" /><label for="category" class="label">По категориям</label></li>
    </div></fieldset></div><br> <div><fieldset class="fieldset-auto-width"><div class="faset-cap">Категории</div><div class="fieldset-content">
    
    <li class="box-group"><input type="checkbox" name="news" id="news" class="bigbox" disabled /><label for="news" class="label">Новости</label></li>
    <li class="box-group"><input type="checkbox" name="abitur" id="abitur" class="bigbox" disabled /><label for="abitur" class="label">Абитуриенту</label></li>
    <li class="box-group"><input type="checkbox" name="science" id="science" class="bigbox" disabled /><label for="science" class="label">Наука</label></li>
    <li class="box-group"><input type="checkbox" name="people" id="people" class="bigbox" disabled /><label for="people" class="label">Люди</label></li>
    <li class="box-group"><input type="checkbox" name="docs" id="docs" class="bigbox" disabled /><label for="docs" class="label">Документы</label></li>
    
    </div></fieldset></div><br> <div><fieldset class="fieldset-auto-width"><div class="faset-cap">Факультеты</div><div class="fieldset-content">
    <li class="box-group"><input type="checkbox" name="geo" id="geo" class="bigbox" disabled /><label for="geo" class="label">Институт географии, геологии, туризма и сервиса</label></li>
    <li class="box-group"><input type="checkbox" name="bio" id="bio" class="bigbox" disabled /><label for="bio" class="label">Биологический факультет</label></li>
    <li class="box-group"><input type="checkbox" name="fad" id="fad" class="bigbox" disabled /><label for="fad" class="label">Факультет архитектуры и дизайна</label></li>
    <li class="box-group"><input type="checkbox" name="jour" id="jour" class="bigbox" disabled /><label for="jour" class="label">Факультет журналистики</label></li>
    <li class="box-group"><input type="checkbox" name="fismo" id="fismo" class="bigbox" disabled /><label for="fismo" class="label">Факультет истории, социологии и международных отношений</label></li>
    <li class="box-group"><input type="checkbox" name="fktipm" id="fktipm" class="bigbox" disabled /><label for="fktipm" class="label">Факультет компьютерных технологий и прикладной математики</label></li>
    <li class="box-group"><input type="checkbox" name="fmikn" id="fmikn" class="bigbox" disabled /><label for="fmikn" class="label">Факультет математики и компьютерных наук</label></li>
    <li class="box-group"><input type="checkbox" name="fppk" id="fppk" class="bigbox" disabled /><label for="fppk" class="label">Факультет педагогики, психологии и коммуникативистики</label></li>
    <li class="box-group"><input type="checkbox" name="rgf" id="rgf" class="bigbox" disabled /><label for="rgf" class="label">Факультет романо-германской филологии</label></li>
    <li class="box-group"><input type="checkbox" name="fup" id="fup" class="bigbox" disabled /><label for="fup" class="label">Факультет управления и психологии</label></li>
    <li class="box-group"><input type="checkbox" name="ftf" id="ftf" class="bigbox" disabled /><label for="ftf" class="label">Физико-технический факультет</label></li>
    <li class="box-group"><input type="checkbox" name="phil" id="phil" class="bigbox" disabled /><label for="phil" class="label">Филологический факультет</label></li>
    <li class="box-group"><input type="checkbox" name="fhivt" id="fhivt" class="bigbox" disabled /><label for="fhivt" class="label">Факультет химии и высоких технологий</label></li>
    <li class="box-group"><input type="checkbox" name="hgf" id="hgf" class="bigbox" disabled /><label for="hgf" class="label">Художественно-графический факультет</label></li>
    <li class="box-group"><input type="checkbox" name="econ" id="econ" class="bigbox" disabled /><label for="econ" class="label">Экономический факультет</label></li>
    <li class="box-group"><input type="checkbox" name="law" id="law" class="bigbox" disabled /><label for="law" class="label">Юридический факультет</label></li>
    </div></fieldset></div></div></span>
        <script>
               document.getElementById("query-field").value = "{0}";
               document.title = "{0} - информационно-поисковая система факультета компьютерных технологий и прикладной математики";
        </script></body> </html>""".format(query_term_corrected))

# http://localhost:8000/search_engine.html
