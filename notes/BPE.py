# 导入第三方 regex 模块。
# 它支持 \p{L}、\p{N} 等 Unicode 字符类别。
import regex


# 编译预分词正则表达式。
# 该规则会把文本分为英文缩写、字母、数字、标点和空白等片段。
# BPE 只允许在同一个 pretoken 内部合并，不能跨越这些片段的边界。
PRETOKEN_PATTERN = regex.compile(
    r"""'(?:[sdmt]|ll|ve|re)| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""
)


def pretokenize(text):
    """
    将 Python 字符串预分词，并把每个片段编码成 UTF-8 bytes。

    参数：
        text：需要处理的 Python 字符串。

    返回：
        list[bytes]，其中每一项都是一个 pretoken。
    """

    # 创建空列表，用于保存最终的 bytes 片段。
    pretokens = []

    # finditer 从左向右返回每一个正则匹配对象。
    for match in PRETOKEN_PATTERN.finditer(text):

        # group() 取得当前匹配到的完整字符串。
        piece = match.group()

        # 正则通常不会产生空匹配，但这里仍然进行保护。
        if piece != "":

            # 先取得完整字符串片段，再把它编码为 UTF-8 bytes。
            encoded_piece = piece.encode("utf-8")

            # 把编码后的 pretoken 加入结果列表。
            pretokens.append(encoded_piece)

    # 空字符串不会产生匹配，因此会自然返回空列表。
    return pretokens


def build_pretoken_counts(text):
    """
    建立 pretoken 频率表。

    返回结构：
        dict[tuple[int, ...], int]

    字典键：
        pretoken 对应的 token ID 元组。

    字典值：
        该 pretoken 在文本中的出现频率。
    """

    # 调用预分词函数，得到 list[bytes]。
    pretokens = pretokenize(text)

    # 创建空字典，用于保存 pretoken 频率。
    pretoken_counts = {}

    # 依次处理每个 pretoken。
    for piece in pretokens:

        # 遍历 bytes 会得到 0～255 的字节整数。
        # 将其转换成 tuple，使它可以作为字典键。
        token_tuple = tuple(piece)

        # 如果该 pretoken 已经出现过，就把频率增加 1。
        if token_tuple in pretoken_counts:
            pretoken_counts[token_tuple] += 1

        # 如果是第一次出现，就把频率初始化为 1。
        else:
            pretoken_counts[token_tuple] = 1

    # 返回聚合后的频率表。
    return pretoken_counts


def count_weighted_pairs(pretoken_counts):
    """
    加权统计所有 pretoken 内部的相邻 token pair。

    返回结构：
        dict[tuple[int, int], int]

    注意：
        不统计两个不同 pretoken 之间的 pair。
    """

    # 创建新的 pair 频率字典。
    pair_counts = {}

    # items() 同时取得 pretoken 元组和它的频率。
    for pretoken, frequency in pretoken_counts.items():

        # 长度为 n 的 pretoken 中有 n - 1 个相邻位置。
        for i in range(len(pretoken) - 1):

            # 取当前位置和下一个位置，组成有顺序的二元组。
            pair = (pretoken[i], pretoken[i + 1])

            # 如果该 pair 已经出现过，就增加整个 pretoken 的频率。
            if pair in pair_counts:
                pair_counts[pair] += frequency

            # 第一次遇到时，初始值也应是 pretoken 的频率。
            else:
                pair_counts[pair] = frequency

    # 返回全部 pair 的加权频率。
    return pair_counts


def merge_pair(tokens, pair, new_token_id):
    """
    在一个 token 序列中，从左向右非重叠合并指定 pair。

    参数：
        tokens：list[int]，原 token 序列。
        pair：tuple[int, int]，需要合并的 token pair。
        new_token_id：合并后使用的新 token ID。

    返回：
        合并后的新 list[int]。
    """

    # 创建新列表，不直接修改传入的原列表。
    merged_tokens = []

    # i 表示当前正在检查的下标。
    i = 0

    # 只要 i 没有越过列表末尾，就继续处理。
    while i < len(tokens):

        # 首先保证当前位置后面还有一个 token。
        has_next_token = i + 1 < len(tokens)

        # 只有存在下一个 token 时，才能组成相邻 pair。
        if has_next_token:

            # 把当前位置的两个 token 组成二元组。
            current_pair = (tokens[i], tokens[i + 1])

        # 如果当前位置已经是最后一个位置，就无法组成 pair。
        else:
            current_pair = None

        # 如果当前位置恰好匹配指定 pair，就执行合并。
        if current_pair == pair:

            # 用一个新的 token ID 替换两个旧 token。
            merged_tokens.append(new_token_id)

            # 两个旧 token 都已经被使用，因此跨过两个位置。
            i += 2

        # 如果当前位置不匹配指定 pair，就保留当前 token。
        else:
            merged_tokens.append(tokens[i])

            # 只处理了一个 token，因此向右移动一个位置。
            i += 1

    # 返回新列表。
    return merged_tokens


def merge_pair_in_counts(pretoken_counts, pair, new_token_id):
    """
    将指定 pair 应用于整个 pretoken 频率表。

    每个 pretoken 独立合并，不允许跨 pretoken 边界。
    """

    # 创建新的频率表，避免在遍历时修改原字典。
    new_counts = {}

    # 遍历每一种唯一 pretoken 及其原频率。
    for pretoken, frequency in pretoken_counts.items():

        # merge_pair 接收 list，因此先把 tuple 转换成 list。
        token_list = list(pretoken)

        # 调用统一的非重叠合并函数。
        merged_list = merge_pair(
            token_list,
            pair,
            new_token_id
        )

        # 字典键不能使用 list，因此重新转换成 tuple。
        merged_tuple = tuple(merged_list)

        # 不同旧 pretoken 可能得到相同的新 tuple。
        # 此时应将它们的频率相加。
        if merged_tuple in new_counts:
            new_counts[merged_tuple] += frequency

        # 如果该新 tuple 首次出现，就保留原 pretoken 的频率。
        else:
            new_counts[merged_tuple] = frequency

    # 返回本轮合并后的新频率表。
    return new_counts


def choose_best_pair(pair_counts, vocab):
    """
    选择本轮需要合并的最高频 pair。

    并列规则：
        频率相同时，选择 bytes 二元组字典序更大的 pair。

    明确规定并列规则，可以保证相同输入每次得到相同结果。
    """

    # 如果频率表为空，说明当前已经没有可合并 pair。
    if len(pair_counts) == 0:
        return None

    # best_pair 暂时设为空。
    best_pair = None

    # 依次检查每一种 pair。
    for pair in pair_counts:

        # 第一次循环时，直接把当前 pair 设为最优 pair。
        if best_pair is None:
            best_pair = pair
            continue

        # 取得当前 pair 的频率。
        current_frequency = pair_counts[pair]

        # 取得目前最优 pair 的频率。
        best_frequency = pair_counts[best_pair]

        # 当前 pair 频率更高时，直接更新。
        if current_frequency > best_frequency:
            best_pair = pair

        # 频率相同时，执行确定性的字节字典序比较。
        elif current_frequency == best_frequency:

            # 找到当前 pair 左 token 代表的 bytes。
            current_left = vocab[pair[0]]

            # 找到当前 pair 右 token 代表的 bytes。
            current_right = vocab[pair[1]]

            # 组成当前 pair 的 bytes 二元组。
            current_bytes_pair = (current_left, current_right)

            # 找到目前最优 pair 左 token 代表的 bytes。
            best_left = vocab[best_pair[0]]

            # 找到目前最优 pair 右 token 代表的 bytes。
            best_right = vocab[best_pair[1]]

            # 组成目前最优 pair 的 bytes 二元组。
            best_bytes_pair = (best_left, best_right)

            # 字典序更大的 pair 胜出。
            if current_bytes_pair > best_bytes_pair:
                best_pair = pair

    # 返回最终选中的整数 ID pair。
    return best_pair



def show_pretoken_counts(pretoken_counts, vocab):
    """
    把 pretoken 频率表转换成更容易阅读的形式。

    参数：
        pretoken_counts：
            dict[tuple[int, ...], int]

        vocab：
            dict[int, bytes]

    返回：
        list[tuple[list[bytes], int]]

    贯穿示例第一轮训练前：

        pretoken_counts = {
            (97, 98): 1,
            (32, 97, 98, 97, 98, 97, 98): 1,
            (32, 97, 98, 97, 98): 1
        }

    转换后：

        [
            ([b"a", b"b"], 1),
            ([b" ", b"a", b"b", b"a", b"b", b"a", b"b"], 1),
            ([b" ", b"a", b"b", b"a", b"b"], 1)
        ]

    这个函数只用于显示训练过程，不修改 vocab 或 pretoken_counts。
    """

    # 创建结果列表。
    readable_counts = []

    # 遍历每一种 pretoken 及其频率。
    for pretoken, frequency in pretoken_counts.items():

        # 保存当前 pretoken 中每个 token ID 所代表的 bytes。
        byte_parts = []

        # 按照 pretoken 内部的原顺序查找词表。
        for token_id in pretoken:
            byte_parts.append(vocab[token_id])

        # 把可读的 bytes 列表及其频率加入结果。
        readable_counts.append((byte_parts, frequency))

    # 返回仅用于显示的结果。
    return readable_counts


def train_byte_bpe(
    text,
    vocab_size,
    min_frequency=1,
    show_steps=False
):
    """
    训练带预分词边界的 byte-level BPE。

    贯穿示例：

        text = "ab ababab abab"
        vocab_size = 260
        min_frequency = 1

    正则预分词结果：

        [
            b"ab",
            b" ababab",
            b" abab"
        ]

    转换成初始 token ID 元组：

        {
            (97, 98): 1,

            (32, 97, 98, 97, 98, 97, 98): 1,

            (32, 97, 98, 97, 98): 1
        }

    其中：

        32 -> b" "
        97 -> b"a"
        98 -> b"b"

    第一轮：

        最高频 pair：
            (97, 98)

        出现频率：
            6

        创建：
            256 -> b"ab"

        频率表变为：

            {
                (256,): 1,
                (32, 256, 256, 256): 1,
                (32, 256, 256): 1
            }

    第二轮：

        最高频 pair：
            (256, 256)

        出现频率：
            3

        创建：
            257 -> b"abab"

        频率表变为：

            {
                (256,): 1,
                (32, 257, 256): 1,
                (32, 257): 1
            }

    第三轮：

        最高频 pair：
            (32, 257)

        出现频率：
            2

        创建：
            258 -> b" abab"

        频率表变为：

            {
                (256,): 1,
                (258, 256): 1,
                (258,): 1
            }

    第四轮：

        最高频 pair：
            (258, 256)

        出现频率：
            1

        创建：
            259 -> b" ababab"

        最终频率表：

            {
                (256,): 1,
                (259,): 1,
                (258,): 1
            }

    最终三个 pretoken 分别表示：

        256 -> b"ab"
        259 -> b" ababab"
        258 -> b" abab"

    因此，按照原始顺序拼接后仍为：

        b"ab" + b" ababab" + b" abab"

        == b"ab ababab abab"
    """

    # byte-level BPE 至少需要包含 256 个基础字节 token。
    if vocab_size < 256:
        raise ValueError("vocab_size 不能小于 256")

    # pair 的最低合并频率必须至少为 1。
    if min_frequency < 1:
        raise ValueError("min_frequency 不能小于 1")

    # 创建空词表。
    vocab = {}

    # 建立 0～255 共 256 个基础 token。
    for token_id in range(256):

        # ID 为 i 的基础 token 对应单字节 bytes([i])。
        vocab[token_id] = bytes([token_id])

    # 示例中：
    #
    # vocab[32] == b" "
    # vocab[97] == b"a"
    # vocab[98] == b"b"

    # 创建空列表，按顺序保存训练得到的合并规则。
    merges = []

    # 对原字符串进行预分词，并聚合相同的 pretoken。
    #
    # 示例得到：
    #
    # {
    #     (97, 98): 1,
    #     (32, 97, 98, 97, 98, 97, 98): 1,
    #     (32, 97, 98, 97, 98): 1
    # }
    pretoken_counts = build_pretoken_counts(text)

    # 第一轮的编号为 1。
    round_number = 1

    # 根据参数决定是否输出训练过程。
    if show_steps:
        print("原字符串：", text)

        # 示例输出：
        # [b'ab', b' ababab', b' abab']
        print("预分词结果：", pretokenize(text))

        print("初始 token 状态：")
        print(show_pretoken_counts(pretoken_counts, vocab))
        print("-" * 70)

    # 词表未达到目标大小时，继续执行训练。
    while len(vocab) < vocab_size:

        # 每一轮都根据当前 token 状态重新统计相邻 pair。
        #
        # 示例第一轮得到：
        #
        # {
        #     (97, 98): 6,
        #     (98, 97): 3,
        #     (32, 97): 2
        # }
        pair_counts = count_weighted_pairs(pretoken_counts)

        # 从 pair_counts 中选择频率最高的 pair。
        #
        # 示例第一轮：
        # best_pair = (97, 98)
        best_pair = choose_best_pair(pair_counts, vocab)

        # 如果不存在相邻 pair，说明所有 pretoken 都只剩一个 token。
        if best_pair is None:
            break

        # 读取最高频 pair 的频率。
        #
        # 示例第一轮：
        # best_frequency = 6
        best_frequency = pair_counts[best_pair]

        # 最高频 pair 也达不到最低频率时停止训练。
        if best_frequency < min_frequency:
            break

        # token ID 始终连续，因此当前词表长度就是下一个新 ID。
        #
        # 四轮中依次得到：
        # 256、257、258、259
        new_token_id = len(vocab)

        # 取得最高频 pair 左侧的 token ID。
        left_id = best_pair[0]

        # 取得最高频 pair 右侧的 token ID。
        right_id = best_pair[1]

        # 根据词表查出左 token 实际代表的 bytes。
        left_bytes = vocab[left_id]

        # 根据词表查出右 token 实际代表的 bytes。
        right_bytes = vocab[right_id]

        # 按照原顺序拼接左右两部分 bytes。
        #
        # 第一轮：
        # b"a" + b"b" == b"ab"
        #
        # 第二轮：
        # b"ab" + b"ab" == b"abab"
        #
        # 第三轮：
        # b" " + b"abab" == b" abab"
        #
        # 第四轮：
        # b" abab" + b"ab" == b" ababab"
        new_token_bytes = left_bytes + right_bytes

        # 将新 token 加入词表。
        vocab[new_token_id] = new_token_bytes

        # 保存本轮的 bytes pair。
        #
        # 四轮结束后：
        #
        # merges = [
        #     (b"a", b"b"),
        #     (b"ab", b"ab"),
        #     (b" ", b"abab"),
        #     (b" abab", b"ab")
        # ]
        merges.append((left_bytes, right_bytes))

        # 输出本轮选择和创建的新 token。
        if show_steps:
            print("第", round_number, "轮")
            print("最高频 ID pair：", best_pair)
            print("pair 频率：", best_frequency)
            print("对应 bytes pair：", (left_bytes, right_bytes))
            print(
                "创建新 token：",
                new_token_id,
                "->",
                new_token_bytes
            )

        # 在所有 pretoken 内执行本轮非重叠合并。
        #
        # 第一轮之后：
        #
        # {
        #     (256,): 1,
        #     (32, 256, 256, 256): 1,
        #     (32, 256, 256): 1
        # }
        pretoken_counts = merge_pair_in_counts(
            pretoken_counts,
            best_pair,
            new_token_id
        )

        # 输出合并后的状态。
        if show_steps:
            print("合并后的 token 状态：")
            print(show_pretoken_counts(pretoken_counts, vocab))
            print("-" * 70)

        # 只有本轮成功创建并应用了新 token 后，轮数才增加。
        round_number += 1

    # 返回最终词表、合并规则和训练后的频率表。
    return vocab, merges, pretoken_counts


if __name__ == "__main__":

    # 使用贯穿整份代码的训练示例。
    example_text = "ab ababab abab"

    # 初始词表中有 256 个基础 token。
    #
    # 这个例子最终产生 4 条不同的合并规则：
    #
    # 256 -> b"ab"
    # 257 -> b"abab"
    # 258 -> b" abab"
    # 259 -> b" ababab"
    #
    # 因此目标词表大小设为：
    #
    # 256 + 4 = 260
    target_vocab_size = 260

    # 最后一轮 pair 的频率为 1。
    # 因此最低频率必须设为 1，才能完成全部四轮。
    minimum_frequency = 1

    # 开始训练，并输出每一轮的变化。
    vocab, merges, final_counts = train_byte_bpe(
        text=example_text,
        vocab_size=target_vocab_size,
        min_frequency=minimum_frequency,
        show_steps=True
    )

    # 输出训练结束后的整体结果。
    print("训练结束")

    # 预期结果为 260。
    print("最终词表大小：", len(vocab))

    # 预期结果为 4。
    print("实际合并次数：", len(merges))

    # 输出四条 bytes 合并规则。
    print("合并规则：", merges)

    # 最终频率表中的每个 pretoken 都只剩一个 token。
    #
    # 预期：
    #
    # {
    #     (256,): 1,
    #     (259,): 1,
    #     (258,): 1
    # }
    print("最终频率表：", final_counts)

    # 输出训练产生的所有新词表项。
    print("新词表项：")

    for token_id in range(256, len(vocab)):
        print(token_id, vocab[token_id])

    # 验证每条成功的 merge 都恰好产生一个新词表项。
    assert len(vocab) == 256 + len(merges)
