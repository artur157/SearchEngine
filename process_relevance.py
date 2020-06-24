from matplotlib.pyplot import (axes,axis,title,legend,figure,
                               xlabel,ylabel,xticks,yticks,
                               xscale,yscale,text,grid,
                               plot,scatter,errorbar,hist,polar,
                               contour,contourf,colorbar,clabel,
                               imshow, show, xlim, ylim)
from mpl_toolkits.mplot3d import Axes3D
from numpy import (linspace,logspace,zeros,ones,outer,meshgrid,
                   pi,sin,cos,sqrt,exp)
from numpy.random import normal
#%matplotlib inline


word = 'бо'
dict_titles = {}   # url -> title
dict_rels = {}     # url -> relevance (0  0.5  1)
total_rel = 0


def outtofile(modelstr, url_list):
    with open("M:\\" + word + "_" + modelstr + "_rels.txt", "w", encoding='utf-8') as file:
        for url in url_list:
            file.write(url+'\n')
        file.write('\n')
        for title in [dict_titles[url] for url in url_list]:
            file.write(title+'\n')
        file.write('\n')
        for rel in [dict_rels[url] for url in url_list]:
            file.write(str(rel) + '\n')
        file.write('\n')


def get_n_write_num_rel_docs(modelstr, url_list):
    total_rel_part = 0
    for url in url_list:
        total_rel_part += dict_rels[url]

    p = total_rel_part / len(url_list)
    r = total_rel_part / total_rel

    with open("M:\\" + word + "_" + modelstr + "_rels.txt", "a", encoding='utf-8') as file:
        file.write('Кол-во релев. док-ов выданных моделью (с поправкой на L-меру): ' + str(total_rel_part) + '\n')
        file.write('Кол-во выданных док-ов: ' + str(len(url_list)) + '\n')
        file.write('Кол-во релев. док-ов (с поправкой на L-меру): ' + str(total_rel) + '\n')
        file.write('Точность: ' + str(round(p, 3)) + '\n')
        file.write('Полнота: ' + str(round(r, 3)) + '\n')
        if p+r > 0:
            file.write('L-мера: ' + str(round(2*p*r/(p+r), 3)) + '\n')
        else:
            file.write('L-мера: 0' + '\n')
        file.write('\n')

    with open("M:\\" + word + "_total_results.txt", "a", encoding='utf-8') as file:
        file.write(modelstr + '\n')
        file.write('Кол-во релев. док-ов выданных моделью (с поправкой на L-меру): ' + str(total_rel_part) + '\n')
        file.write('Кол-во выданных док-ов: ' + str(len(url_list)) + '\n')
        file.write('Кол-во релев. док-ов (с поправкой на L-меру): ' + str(total_rel) + '\n')
        file.write('Точность: ' + str(round(p, 3)) + '\n')
        file.write('Полнота: ' + str(round(r, 3)) + '\n')
        if p+r > 0:
            file.write('L-мера: ' + str(round(2*p*r/(p+r), 3)) + '\n')
        else:
            file.write('L-мера: 0' + '\n')
        file.write('\n')

    # а теперь ещё хотим график т-н построить
    total_rel_part = 0
    tmp_len = 0
    points_x = []
    points_y = []

    for url in url_list:
        total_rel_part += dict_rels[url]
        tmp_len += 1
        p = total_rel_part / tmp_len
        r = total_rel_part / total_rel
        points_x.append(r)
        points_y.append(p)

    plot(points_x, points_y)


def form_urls_n_dicts(modelstr):
    with open("M:\\"+word+"_"+modelstr+".txt", "r", encoding='utf-8') as file:
        fromfile = file.read()
    lines = fromfile.split('$')
    cur_urls = []
    for line in lines[:-1]:
        sp = line.split('&')
        cur_urls.append(sp[0])
        dict_titles[sp[0]] = sp[1]
    return cur_urls




bm25_urls = form_urls_n_dicts('bm25')
cbow_urls = form_urls_n_dicts('cbow')
cbow_h_urls = form_urls_n_dicts('cbow_h')
sg_urls = form_urls_n_dicts('sg')
sg_h_urls = form_urls_n_dicts('sg_h')
dbow_urls = form_urls_n_dicts('dbow')
dbow_h_urls = form_urls_n_dicts('dbow_h')
dm_urls = form_urls_n_dicts('dm')
dm_h_urls = form_urls_n_dicts('dm_h')

# печатаем длины выданных моделями док-ов
print([len(spi) for spi in [bm25_urls, cbow_urls, cbow_h_urls, sg_urls, sg_h_urls, dbow_urls, dbow_h_urls, dm_urls, dm_h_urls]])
# формируем множество url
set_urls = set.union(set(bm25_urls), set(cbow_urls), set(cbow_h_urls), set(sg_urls), set(sg_h_urls), set(dbow_urls), set(dbow_h_urls), set(dm_urls), set(dm_h_urls))
print('Всего url:', len(set_urls))

# если что-то было, то вспоминаем. Что, зря что ли оценивали
'''
with open("M:\\" + word + "_exp.txt", "r", encoding='utf-8') as efile:
    rels_from_file = efile.read()
lines = rels_from_file.split('$')
for line in lines:
    sp = line.split('&')
    dict_rels[sp[0]] = float(sp[1])
    total_rel += dict_rels[sp[0]]
'''
'''
# собираем оценки ИЛИ ...
order = len(dict_rels)
for url in set_urls:

    if not url in dict_rels:
        print('Вопрос', str(order))
        order += 1
        print(url)
        print(dict_titles[url])
        dict_rels[url] = float(input('0  0.5  1?'))
        total_rel += dict_rels[url]

all_url_list = list(set_urls)
with open("M:\\" + word + "_expert.txt", "w", encoding='utf-8') as efile:
    all_url_rel_list = [u+'&'+str(dict_rels[u])  for u in all_url_list]
    efile.write('$'.join(all_url_rel_list))


# ... читаем оценки с файла!
'''
with open("M:\\" + word + "_expert.txt", "r", encoding='utf-8') as efile:
    rels_from_file = efile.read()
lines = rels_from_file.split('$')
for line in lines:
    sp = line.split('&')
    dict_rels[sp[0]] = float(sp[1])
    total_rel += dict_rels[sp[0]]


# теперь красиво выведем в файл
outtofile('bm25', bm25_urls)
outtofile('cbow', cbow_urls)
outtofile('cbow_h', cbow_h_urls)
outtofile('sg', sg_urls)
outtofile('sg_h', sg_h_urls)
outtofile('dbow', dbow_urls)
outtofile('dbow_h', dbow_h_urls)
outtofile('dm', dm_urls)
outtofile('dm_h', dm_h_urls)

# считаем кол-во релевантных док-ов и выдаем в файл
get_n_write_num_rel_docs('bm25', bm25_urls)
get_n_write_num_rel_docs('cbow', cbow_urls)
get_n_write_num_rel_docs('cbow_h', cbow_h_urls)
get_n_write_num_rel_docs('sg', sg_urls)
get_n_write_num_rel_docs('sg_h', sg_h_urls)
get_n_write_num_rel_docs('dbow', dbow_urls)
get_n_write_num_rel_docs('dbow_h', dbow_h_urls)
get_n_write_num_rel_docs('dm', dm_urls)
get_n_write_num_rel_docs('dm_h', dm_h_urls)



xlim(0 ,1)
ylim(0, 1)
grid()
legend(['bm-25', 'cbow', 'cbow_h', 'sg', 'sg_h', 'dbow', 'dbow_h', 'dm', 'dm_h'])
show()





