from collections import defaultdict, Counter  # 导入所需库

# 构建一个玩具数据集
corpus = [
    "我喜欢吃苹果",
    "我喜欢吃香蕉",
    "她喜欢吃葡萄",
    "他不喜欢吃香蕉",
    "他喜欢吃苹果",
    "她喜欢吃草莓",
]


def tokenize(text):
    return [char for char in text]  # 将文本分解为单字列表


# 定义计算N-Gram词频的函数
def count_ngrams(corpus, n):
    ngrams_count = defaultdict(Counter)  # 创建一个字典，存储N-Gram计数

    for text in corpus:  # 遍历语料库中的每个文本
        tokens = tokenize(text)  # 对文本进行分词
        for i in range(len(tokens) - n + 1):  # 遍历分词结果，生成N-Gram
            ngram = tuple(tokens[i : i + n])  # 创建一个N-Gram元组
            prefix = ngram[:-1]  # 获取N-Gram的前缀
            token = ngram[-1]  # 获取N-Gram的目标单字
            ngrams_count[prefix][token] += 1  # 更新N-Gram计数
    return ngrams_count


bigram_counts = count_ngrams(corpus, 2)  # 计算Bigram词频

# 打印Bigram词频
print("Bigram词频：")

for prefix, counts in bigram_counts.items():
    print("{}: {}".format("".join(prefix), dict(counts)))


# 定义计算N-Gram出现概率的函数
def ngram_probabilities(ngram_counts):
    ngram_probs = defaultdict(Counter)  # 创建一个字典，存储N-Gram出现的概率
    for prefix, tokens_count in ngram_counts.items():  # 遍历N-Gram前缀
        total_count = sum(tokens_count.values())  # 计算当前前缀的N-Gram计数
        for token, count in tokens_count.items():  # 遍历每个前缀的N-Gram
            ngram_probs[prefix][token] = count / total_count  # 计算每个N-Gram出现的概率
    return ngram_probs


bigram_probs = ngram_probabilities(bigram_counts)  # 计算Bigram出现的概率

print("\nbigram出现的概率:")  # 打印Bigram概率
for prefix, probs in bigram_probs.items():
    print("{}: {}".format("".join(prefix), dict(probs)))
