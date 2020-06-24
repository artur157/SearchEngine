import gensim
from gensim import corpora
import nltk
import nltk.data
#nltk.download('punkt')
#tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
import pymorphy2
morph = pymorphy2.MorphAnalyzer()
from gensim.models import Word2Vec, Doc2Vec, KeyedVectors
import multiprocessing as mp
import gensim.downloader as api
import cython
from datetime import datetime
import time
from os import walk


def senttolist(sent):
    word_list = nltk.word_tokenize(sent, language="russian")
    word_list = [morph.parse(word.lower())[0].normal_form for word in word_list if word.isalpha()]
    #print(word_list)   ПОКАЗЫВАЕТ КАК РАЗДЕЛИЛОСЬ ПО ПРЕДЛОЖЕНИЯМ, УБРАЛИ ПУНКТУАЦИЮ И ПРИВЕЛИ В Н. Ф.
    return word_list


def preprocess(text):
    sentences = []
    for sent in nltk.sent_tokenize(text, language="russian"):
        sent_list = [senttolist(sent)]
        if len(sent_list)>0:
            sentences += sent_list

    return sentences


def process_files(num):
    text = ''
    with open("M:\\corpus_6281\\" + str(num) + ".txt", "r", encoding='utf-8') as file:
        text = file.read()

    if num % 200 == 0:
        print(str(num))

    return preprocess(text)


def get_query_vector(query):
    # загружаем модель
    model = Word2Vec.load("F:\\my_word2vec")

    result_vector = []
    for i in range(300):
        result_vector.append(0)

    word_list = senttolist(query)
    word_list_len = len(word_list)

    # прибавить result_vector к model[word]
    for word in word_list:
        word_vector = model[word]
        for i in range(300):
            result_vector[i] += word_vector[i]

    for i in range(300):
        result_vector[i] /= word_list_len


def create_tagged_document(list_of_list_of_words):
    for i, list_of_words in enumerate(list_of_list_of_words):
        yield gensim.models.doc2vec.TaggedDocument(list_of_words, [i])


if __name__ == '__main__':
    '''
    start_time = datetime.now()

    texts = []
    texts_closed = []

    #nums = [(i,) for i in range(10)]
    nums = []
    for (dirpath, dirname, filename) in walk("M:\\corpus_6281"):
        for file in filename:
            if '.txt' in file:
                nums.append((int(file[:file.find('.')]),))

    with mp.Pool(mp.cpu_count()) as pool:
        texts_closed = pool.starmap(process_files, nums)

    print('preprocessing: ', str(datetime.now() - start_time))
    start_time = datetime.now()

    # спец подготовка данных для doc2vec
    doc2vec_docs = []
    for lst in texts_closed:
        doc2vec_sents = []
        for llst in lst:
            doc2vec_sents += llst
        doc2vec_docs.append(doc2vec_sents)
    doc2vec_train_data = list(create_tagged_document(doc2vec_docs))

    print('tagging documents: ', str(datetime.now() - start_time))
    start_time = datetime.now()

    for list in texts_closed:
        texts += list
    #texts = lambda texts_closed: [el for lst in texts_closed for el in lst]

    print('closed -> opened: ', str(datetime.now() - start_time))
    texts = [value for value in texts if value]
    '''
    '''
    print('pickling...')
    start_time = datetime.now()
    with open("M:\\corpus_6281_w2v_pickle.txt", "w", encoding='utf-8') as file:
        pre_list = []
        for spi in texts:
            pre_list.append('^'.join(spi))
        file.write('@'.join(pre_list))

    with open("M:\\corpus_6281_d2v_pickle.txt", "w", encoding='utf-8') as file:
        pre_list = []
        for spi in doc2vec_docs:
            pre_list.append('^'.join(spi))
        file.write('@'.join(pre_list))
    print('pickled time: ', str(datetime.now() - start_time))
    '''

    #new_list = []
    #with open("M:\\corpus_6281_pickle.txt", "r", encoding='utf-8') as file:
    #    inf = file.read()
    #    new_list = inf.split('@')
    #    new_list = [elem.split('^') for elem in new_list]

    #dictionary = corpora.Dictionary(texts)   # Create dictionary
    #print(dictionary)    # Get information about the dictionary

    '''
    #   ПРОВЕРКА РАБОТЫ МОДЕЛИ
    model = gensim.models.Word2Vec.load("F:\\my_word2vec")

    text = ''
    with open("M:\\corpus_3450\\432.txt", "r", encoding='utf-8') as file:
        text = file.read()
    get_query_vector(text)

    #the_word = morph.parse('декан')[0].normal_form
    #print(the_word)
    #print(model[the_word])
    #print(model.most_similar(the_word))

    '''

    print('training...')
    '''
    start_time = datetime.now()
    model = Word2Vec(texts, size=300, workers=mp.cpu_count())  # cbow
    print('training model 0: ', str(datetime.now() - start_time))

    start_time = datetime.now()
    model.save("F:\\my_word2vec_0")
    print('saving model 0: ', str(datetime.now() - start_time))
    '''
    # defaults: sentences=None, corpus_file=None, size=100, alpha=0.025, window=5, min_count=5, max_vocab_size=None, sample=0.001, seed=1, workers=3,
    # min_alpha=0.0001, sg=0, hs=0, negative=5, ns_exponent=0.75, cbow_mean=1, hashfxn=<built-in function hash>, iter=5, null_word=0, trim_rule=None,
    # sorted_vocab=1, batch_words=10000, compute_loss=False, callbacks=(), max_final_vocab=None
    '''
    start_time = datetime.now()
    model1 = Word2Vec(texts, size=300, min_count=5, window=5, sample=1e-5, sg=0, iter=10, workers=mp.cpu_count())  # min_count=5, negative=5
    print('training model 1: ', str(datetime.now() - start_time))

    start_time = datetime.now()
    model1.save("F:\\my_word2vec_1_")
    print('saving model 1: ', str(datetime.now() - start_time))

    start_time = datetime.now()
    model2 = Word2Vec(texts, size=300, min_count=5, window=10, sample=1e-5, sg=1, iter=10, workers=mp.cpu_count())  # min_count=5, negative=5
    print('training model 2: ', str(datetime.now() - start_time))

    start_time = datetime.now()
    model2.save("F:\\my_word2vec_2_")
    print('saving model 2: ', str(datetime.now() - start_time))

    start_time = datetime.now()
    model3 = gensim.models.doc2vec.Doc2Vec(size=300, min_count=5, window=10, sample=1e-5, dm=0, dbow_words=1, iter=10, workers=mp.cpu_count())
    model3.build_vocab(doc2vec_train_data)
    model3.train(doc2vec_train_data, total_examples=model3.corpus_count, epochs=model3.epochs)
    #print(model.infer_vector(['australian', 'captain', 'elected', 'to', 'bowl']))   ВЕКТОР ПРЕДЛОЖЕНИЯ
    print('training model 3: ', str(datetime.now() - start_time))

    start_time = datetime.now()
    model3.save("F:\\my_doc2vec_1_")
    print('saving model 3: ', str(datetime.now() - start_time))

    start_time = datetime.now()
    model4 = gensim.models.doc2vec.Doc2Vec(size=300, min_count=5, window=10, sample=1e-5, dm=1, iter=10, workers=mp.cpu_count())
    model4.build_vocab(doc2vec_train_data)
    model4.train(doc2vec_train_data, total_examples=model4.corpus_count, epochs=model4.epochs)
    print('training model 4: ', str(datetime.now() - start_time))

    start_time = datetime.now()
    model4.save("F:\\my_doc2vec_2_")
    print('saving model 4: ', str(datetime.now() - start_time))
    '''
    model8 = gensim.models.Word2Vec.load("F:\\my_word2vec_1")
    print(model8.most_similar('дрон'))