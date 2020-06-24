import os
import sys
import json
import re
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
from gensim.models import Word2Vec, Doc2Vec
from gensim.models import KeyedVectors
import multiprocessing as mp
import gensim.downloader as api
import nltk
import nltk.data
from nltk.corpus import stopwords
import pymorphy2
import docx2txt
from io import BytesIO
import io
from pdfminer.converter import TextConverter
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfpage import PDFPage
from datetime import datetime


# https://kubsu.ru/sites/default/files/page/jan_2018.pdf   https://kubsu.ru/sites/default/files/insert/page/polozhenie_o_pervichnoy_profsoyuznoy_organizacii_0.pdf
# https://kubsu.ru/sites/default/files/faculty/informacionnoe_pismo_no_1_2018_00000003.doc
START_URL = 'https://kubsu.ru'   # https://kubsu.ru/fktipm     https://www.kubsu.ru/sites/default/files/insert/page/chugaev_a._p._bibliogr._ukazatel.docx
ALLOWED_DOMAINS = {'kubsu.ru'}  # kubsu.ru/fktipm
INDEX_NAME = 'kubsuuu'
TIMEOUT = 5                 # интервал обращения за страницами
MAX_RETRY = 3               # макс. кол-во попыток получить страницу
total = 0


def normalize_links(current_url, links):
    result = [normalize_link(current_url, link) for link in links]
    return result


def normalize_link(current_url, link):    # дело в том, что link - это не url, а лишь концовка его
    url_with_tail = urljoin(current_url, link[0])
    normalized = remove_tail(url_with_tail)

    # удаляем дубликаты
    normalized = normalized.replace('http:', 'https:')
    normalized = normalized.replace('ru/ru', 'ru')
    normalized = normalized.replace('ru/en', 'ru')
    normalized = normalized.replace('www.', '')
    if normalized[-1:] == '/':
        normalized = normalized[0:-1]

    return (normalized, link[1])


def remove_tail(url):
    parsed = urlparse(url)
    result = parsed.scheme + '://' + parsed.netloc + parsed.path
    return result


def link_domain_disallowed(url):    # индексируем только домены факультета     НЕМНОГО ПЕРЕОФОРМИТЬ НАДО

    parsed = urlparse(url[0])

    return parsed.netloc not in ALLOWED_DOMAINS  # ДЛЯ ВСЕГО САЙТА
    #return 'special' in url[0] or 'vk.com' in url[0] or 'fktipm' not in url[0] and '87' not in url[0] and '295' not in url[0] and 'granty_i_prokty' not in url[0]


def is_image(url):       # картинки не индексируем
    image_suffixes = ['.png', '.jpg', 'jpeg', '.gif', '.ppt', '.pptx', '.xls', '.xlsx', '.doc', '.txt', '.tex', '.cls', '.zip', '.rar.', '.exe']
    for suffix in image_suffixes:
        if url[0].endswith(suffix):
            return True
    return '@' in url


'''
def is_habr_qa(url):
    return urlparse(url).path.startswith('/qa/')


def kubsu_max_depth(url):    # смотрим чтобы глубина url не была больше 8
    splits = urlparse(url).path.split('/')
    return len(splits) > 8
'''


def kubsu_not_slashed(url):   # смотрим чтобы url не заканчивался слэшем
    return not (url.endswith('/'))


'''
def kubsu_user_limit(url):
    path = urlparse(url).path
    if path.startswith('/users/'):
        splits = path.split('/')
        if splits[-2].startswith('page'):
            try:
                n = int(splits[-2][len('page'):])
                if n >= 10:
                    return True
                else:
                    return False
            except ValueError:
                return True
        else:
            return False
    else:
        return False
'''


def filter_urls(filters, urls):
    if len(filters) == 0:
        return urls
    else:
        return filter(lambda x: not filters[0](x), filter_urls(filters[1:], urls))


def get_filters():
    return [
        link_domain_disallowed,
        is_image
        #is_habr_qa,
        #kubsu_not_slashed
        #kubsu_user_limit,
        #kubsu_max_depth
    ]


'''      НЕ ИСПОЛЬЗУЕТСЯ
def check_response(response):
    return (response.status_code == 200) and (response.headers['Content-Type'].startswith('text/html'))
'''


def get_links(html):     # получаем из страницы ссылки
    soup = BeautifulSoup(html, 'lxml')
    links_in_tags = soup.findAll('a')
    links = []
    for link_in_tags in links_in_tags:
        links.append((link_in_tags.get('href'), link_in_tags.text))
    return links


def get_filtered_links(url, html):    # извлекаем из страницы ссылки и фильтруем из них лишнее
    links = get_links(html)
    normalized_links = normalize_links(url, links)
    filters = get_filters()
    filtered_urls = list(filter_urls(filters, normalized_links))
    return set(filtered_urls)


def save_html(url, html, url_title):      # индексируем
    result = parse(url, html, url_title)  # bs_link['href'])
    if es is not None and result != json.dumps({}):
        '''
        if create_index(es, INDEX_NAME):
            out = store_record(es, INDEX_NAME, result)
            print('Data indexed successfully')
            
        if create_index(es, 'kubsu1'):
            out = store_record(es, 'kubsu1', result[0])
            print('Data indexed successfully')
        if create_index(es, 'kubsu2'):
            out = store_record(es, 'kubsu2', result[1])
            print('Data indexed successfully')'''
        if create_index(es, 'kubsu3'):
            out = store_record(es, 'kubsu3', result[0])
            print('Data indexed successfully')
        if create_index(es, 'kubsu4'):
            out = store_record(es, 'kubsu4', result[1])
            print('Data indexed successfully')


def get_response(url):     # получить страницу по url
    for i in range(MAX_RETRY):
        try:
            if url.endswith(('.doc', '.docx', '.pdf')):
                return requests.get(url, headers=headers, timeout=TIMEOUT, stream=True)
            else:
                return requests.get(url, headers=headers, timeout=TIMEOUT)
        except Exception as ex:
            print("Cannot crawl url {} by reason: {}. Retry in 1 sec".format(url, ex))
            time.sleep(1)
    print("Url {} was not indexed".format(url))
    return None#requests.Response()


def bfs(start_url):
    queue = Queue()           # очередь
    queue.put((start_url, 'Официальный сайт КубГУ'))
    seen_links = {start_url}  # список просмотренных url

    while not (queue.empty()):
        link = queue.get()
        url_title = link[1]
        url = link[0]

        print('processing url ' + url)

        html = get_response(url)

        if html is not None and html.status_code == 200:
            if not url.endswith(('.doc', '.docx', '.pdf')):
                html = html.text

            save_html(url, html, url_title)

            if not url.endswith(('.doc', '.docx', '.pdf')):
                for link in get_filtered_links(url, html):
                    if link[0] not in seen_links:
                        queue.put(link)
                        seen_links.add(link[0])


def create_index(es_object, index_name):
    created = False
    # index settings
    settings = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "filter": {
                    "russian_stop": {
                        "type": "stop",
                        "stopwords": "_russian_"},
                    "russian_stemmer": {
                        "type": "stemmer",
                        "language": "russian"},
                    "bigram_filter": {
                        "type": "shingle",
                        "max_shingle_size": 2,
                        "min_shingle_size": 2,
                        "output_unigrams": "false"
                    },
                    "unigram_bigram_filter": {
                        "type": "shingle",
                        "max_shingle_size": 2,
                        "min_shingle_size": 2,
                        "output_unigrams": "true"
                    }
                },
                "char_filter": {
                    "e_char_filter": {
                        "type": "mapping",
                        "mappings": ["Ё => Е", "ё => е"]
                    }
                },
                "analyzer": {
                    "default": {
                        "char_filter": [
                            "html_strip",
                            "e_char_filter"],
                        "tokenizer": "my_tokenizer",
                        "filter": [
                            "lowercase",
                            "russian_stop",
                            "russian_stemmer"]},
                    "no_stemming": {
                        "char_filter": [
                            "html_strip",
                            "e_char_filter"],
                        "tokenizer": "my_tokenizer",
                        "filter": [
                            "lowercase",
                            "russian_stop"]},
                    "bigrams": {
                        "char_filter": [
                            "html_strip",
                            "e_char_filter"],
                        "tokenizer": "my_tokenizer",
                        "filter": [
                            "lowercase",
                            "russian_stop",
                            "russian_stemmer",
                            "bigram_filter"
                        ]
                    },
                    "bigrams_no_stemming": {
                        "char_filter": [
                            "html_strip",
                            "e_char_filter"],
                        "tokenizer": "my_tokenizer",
                        "filter": [
                            "lowercase",
                            #"russian_stop",
                            "unigram_bigram_filter"
                        ]
                    }
                },
                "tokenizer": {
                    "my_tokenizer": {
                        "type": "standard"
                    }
                }
            }},
        "mappings": {
            "dynamic": "strict",     # выполнять строгую проверку типов входящего документа
            "properties": {
                "title": {
                    "type": "text",
                    "term_vector": "with_positions_offsets",
                    "analyzer": "default",
                    "fields": {
                        "bigrammed": {
                            "type": "text",
                            "analyzer": "bigrams"
                        }
                    }
                },
                "body": {
                    "type": "text",
                    "term_vector": "with_positions_offsets",
                    "analyzer": "default",
                    "fields": {
                        "bigrammed": {
                            "type": "text",
                            "analyzer": "bigrams"
                        }
                    },
                    #"copy_to": ["suggestion"]
                    "copy_to": ["completion"]
                },
                "body_vector": {
                    "type": "dense_vector",
                    "dims": 300
                },
                "suggestion": {
                    "type": "text",
                    "analyzer": "no_stemming",
                    # "fields": {      для фразового суггестера
                    #     "bigrammed": {
                    #         "type": "text",
                    #         "analyzer": "no_stemming_bigrams"
                    #     }
                    # }
                },
                "completion": {
                    "type": "text",
                    "analyzer": "bigrams_no_stemming",
                    "fielddata": True
                },
                "url": {
                    "type": "text"
                },
                "markup": {
                    "type": "keyword"
                }}}}

    try:
        if not es_object.indices.exists(index_name):
            es_object.indices.create(index=index_name, body=settings)
            print('Created Index')
        created = True
    except Exception as ex:
        print(str(ex))
    finally:
        return created


def store_record(elastic_object, index_name, record):
    global total
    is_stored = True
    try:
        #outcome = elastic_object.index(index=index_name, doc_type='pages', body=record)
        outcome = elastic_object.index(index=index_name, body=record)
        print(outcome)
        total += 1
    except Exception as ex:
        print('Error in indexing data')
        print(str(ex))
        is_stored = False
    finally:
        return is_stored


def connect_elasticsearch():
    _es = None
    _es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
    if _es.ping():
        print('Yay Connected')
        print('____________________________________')
    else:
        print('Awww it could not connect!')
        print('____________________________________')
    return _es


def extract_text_from_pdf(bytes):
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle)
    page_interpreter = PDFPageInterpreter(resource_manager, converter)

    fh = bytes
    for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
        page_interpreter.process_page(page)

    text = fake_file_handle.getvalue()

    # close open handles
    converter.close()
    fake_file_handle.close()

    if text:
        return text
    else:
        return ''


def parse(url, html, url_title):     # на входе строка url, на выходе json для хранения в ES
    title = ''
    body = ''    # <section id="section-content" class="section section-content">
    rec = {}

    try:

        if url.endswith('.docx'):
            my_raw_data = BytesIO(html.content)
            body = docx2txt.process(my_raw_data)
            title = 'Документ [docx]' if url_title == '' or url_title.startswith('http') else url_title

        elif url.endswith('.pdf'):
            my_raw_data = BytesIO(html.content)
            body = extract_text_from_pdf(my_raw_data)
            title = 'Документ [pdf]' if url_title == '' or url_title.startswith('http') else url_title

        else:

            htmlws = re.compile('<').sub(' <', html)   # ТО ЧТО ПОМОГЛО НЕ СЛИПАТЬСЯ !!!

            soup = BeautifulSoup(htmlws, 'lxml')

            # хотим удалить теги script
            for s in soup.select('script'):
                s.decompose()

            # хотим удалить теги aside
            for s in soup.select('aside'):
                s.decompose()

            title_section = soup.select('title')
            body_section = soup.select('#section-content')
            title = title_section[0].text
            title = title[:title.find('|')].strip()  # убрать всё что после |
            body = re.compile('<').sub(' <', body_section[0].text)

        body = re.compile('\s+').sub(' ', body).strip()

        if body != '':

            #body_vector1 = get_word2vec_doc_vector(model1, body)
            #body_vector2 = get_word2vec_doc_vector(model2, body)
            body_vector3 = get_doc2vec_doc_vector(model3, body)
            body_vector4 = get_doc2vec_doc_vector(model4, body)

            # параллельно готовим тексты для обучения моделей
            #with open("M:\\test\\" + str(total) + ".txt", "w", encoding='utf-8') as file:
            #    file.write(body)

            #rec1 = {'title': title, 'body': body, 'body_vector': body_vector1, 'suggestion': body, 'url': url}
            #rec2 = {'title': title, 'body': body, 'body_vector': body_vector2, 'suggestion': body, 'url': url}
            rec3 = {'title': title, 'body': body, 'body_vector': body_vector3, 'suggestion': body, 'url': url}
            rec4 = {'title': title, 'body': body, 'body_vector': body_vector4, 'suggestion': body, 'url': url}
            return [rec3, rec4]
        return json.dumps(rec)
    except Exception as ex:
        print('Exception while parsing')
        print(str(ex))
        return json.dumps(rec)
    #finally:
    #    return json.dumps(rec)


def senttolist(sent, rmv_stop):
    word_list = nltk.word_tokenize(sent, language="russian")
    norm_word_list = [morph.parse(word.lower())[0].normal_form for word in word_list if word.isalpha()]
    if rmv_stop:
        norm_word_list_without_stops = [w for w in norm_word_list if not w in stop_words]   # удалить из word_list стоп-слова
        return norm_word_list_without_stops
    return norm_word_list


def preprocess(text, rmv_stop):
    norm_words = []
    for sent in nltk.sent_tokenize(text, language="russian"):
        norm_words += senttolist(sent, rmv_stop)
    return norm_words


def get_word2vec_doc_vector(model, doc):
    result_vector = []
    for i in range(300):
        result_vector.append(0)

    word_list = preprocess(doc, True)
    word_list_len = len(word_list)

    if word_list_len > 0:
        # прибавить result_vector к model[word]
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

    return result_vector


def get_doc2vec_doc_vector(model, doc):
    result_vector = []
    for i in range(300):
        result_vector.append(0)

    word_list = preprocess(doc, False)
    word_list_len = len(word_list)

    try:
        if word_list_len > 0:
            result_vector = model.infer_vector(word_list).tolist()
    except Exception as ex:
        print('infer trouble')

    return result_vector


def init_model():
    # Load Word2Vec model
    #model = KeyedVectors.load_word2vec_format("F:\\ruwikiruscorpora_upos_cbow_300_20_2017.bin.gz", binary=True)
    #model.init_sims(replace=True)

    #model = KeyedVectors.load("F:\\ruwikiruscorpora-nobigrams_upos_skipgram_300_5_2018")
    #model.build_vocab
    model = Word2Vec.load("F:\\my_word2vec")
    #vocab_size = len(model.wv.vocab.items())
    #print('Vocabulary: ' + str(vocab_size))
    #print(model.wv.vocab.items())
    #for n in model.most_similar(positive=['факультет_NOUN']):
    #    print(n[0], n[1])
    return model


def reindex(es_object):
    '''
    if es_object.indices.exists(index=INDEX_NAME):
        es_object.indices.delete(index=INDEX_NAME)
    if es_object.indices.exists(index='kubsu1'):
        es_object.indices.delete(index='kubsu1')
    if es_object.indices.exists(index='kubsu2'):
        es_object.indices.delete(index='kubsu2')
    if es_object.indices.exists(index='kubsu3'):
        es_object.indices.delete(index='kubsu3')
    if es_object.indices.exists(index='kubsu4'):
        es_object.indices.delete(index='kubsu4')
        '''
    bfs(START_URL)


if __name__ == '__main__':
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36',
        'Pragma': 'no-cache'
        #'Content-Type': 'text/html',
        #'charset': 'utf-8'
    }
    logging.basicConfig(level=logging.ERROR)

    stop_words = set(stopwords.words('russian'))
    morph = pymorphy2.MorphAnalyzer()
    #model1 = Word2Vec.load("F:\\my_word2vec_1")
    #model2 = Word2Vec.load("F:\\my_word2vec_2")
    model3 = Doc2Vec.load("F:\\my_doc2vec_1")
    model4 = Doc2Vec.load("F:\\my_doc2vec_2")
    print('Models initialized...')
    es = connect_elasticsearch()
    start_time = datetime.now()
    reindex(es)  # ИНДЕКСИРОВАНИЕ
    print('Total: '+str(total))
    print('crawling time: ', str(datetime.now() - start_time))
