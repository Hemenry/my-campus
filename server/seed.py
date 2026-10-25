"""演示数据：python seed.py [--force]

幂等：库里已有用户时直接跳过；--force 会清空重灌（仅限开发库）。
"""

import sys
from datetime import date, datetime, timedelta

from app import create_app
from app.extensions import db
from app.models import (
    Answer,
    Checkin,
    Comment,
    Mistake,
    Notification,
    Plan,
    Post,
    User,
    Wordbook,
    WordEntry,
    utcnow,
)

PASSWORD = "123456"

USERS = [
    ("linyizhou", "林一舟", "计算机系", "2024 级", "星河大学", "在把数学和代码都学明白的路上。"),
    ("zhouzhixia", "周知夏", "数学系", "2023 级", "星河大学", "证明写不完就睡不着。"),
    ("chenjianshan", "陈见山", "物理系", "2023 级", "星河大学", "喜欢把公式讲成人话。"),
    ("xuzhiwei", "许知微", "计算机系", "2024 级", "星河大学", "网络和系统方向，正在准备实习。"),
    ("shenyiran", "沈亦然", "外国语学院", "2022 级", "星河大学", "四六级资料收集爱好者。"),
]

WORDS_A = [
    ("ambiguous", "/æmˈbɪɡjuəs/", "adj. 模糊不清的；有多种解释的", "The wording was deliberately ambiguous.", "这个措辞是故意含糊的。"),
    ("coherent", "/kəʊˈhɪərənt/", "adj. 连贯的；条理清楚的", "She gave a coherent account of the events.", "她对事件做了条理清晰的陈述。"),
    ("abandon", "/əˈbændən/", "v. 放弃；遗弃", "They abandoned the plan after two weeks.", "两周后他们放弃了这个计划。"),
    ("contemplate", "/ˈkɒntəmpleɪt/", "v. 沉思；考虑", "He contemplated moving abroad for a year.", "他考虑出国待一年。"),
    ("deteriorate", "/dɪˈtɪəriəreɪt/", "v. 恶化；变坏", "Her health deteriorated rapidly.", "她的健康状况迅速恶化。"),
    ("inevitable", "/ɪnˈevɪtəbl/", "adj. 不可避免的；必然发生的", "A delay was inevitable in the end.", "最终延期是不可避免的。"),
    ("legitimate", "/lɪˈdʒɪtɪmət/", "adj. 合理的；正当的", "There is a legitimate reason for the question.", "提出这个问题是有正当理由的。"),
    ("negligible", "/ˈneɡlɪdʒəbl/", "adj. 微不足道的；可忽略的", "The difference is negligible.", "这个差别可以忽略不计。"),
    ("resilient", "/rɪˈzɪliənt/", "adj. 有韧性的；能迅速恢复的", "Children are often remarkably resilient.", "孩子的恢复力往往很惊人。"),
    ("scrutiny", "/ˈskruːtəni/", "n. 仔细审查；细看", "The proposal came under close scrutiny.", "该提案受到了严密审查。"),
    ("thrive", "/θraɪv/", "v. 茁壮成长；兴旺", "These plants thrive in poor soil.", "这些植物在贫瘠的土壤里也能长得好。"),
    ("versatile", "/ˈvɜːsətaɪl/", "adj. 多才多艺的；用途广的", "A versatile tool that does many jobs.", "一件能应付多种活儿的工具。"),
    ("compensate", "/ˈkɒmpenseɪt/", "v. 补偿；弥补", "Nothing can compensate for the lost time.", "什么也弥补不了失去的时间。"),
    ("deliberate", "/dɪˈlɪbərət/", "adj. 故意的；深思熟虑的", "It was a deliberate attempt to mislead.", "那是蓄意的误导。"),
    ("elaborate", "/ɪˈlæbərət/", "adj. 精心制作的；复杂的", "He refused to elaborate on the plan.", "他拒绝详细说明这个计划。"),
    ("facilitate", "/fəˈsɪlɪteɪt/", "v. 促进；使便利", "The tool facilitates group discussion.", "这个工具便于开展小组讨论。"),
    ("inherent", "/ɪnˈhɪərənt/", "adj. 内在的；固有的", "There are risks inherent in the design.", "这个设计本身带有风险。"),
    ("notorious", "/nəʊˈtɔːriəs/", "adj. 臭名昭著的", "The road is notorious for accidents.", "这条路因事故频发而出了名。"),
    ("perceive", "/pəˈsiːv/", "v. 察觉；理解", "Students perceive the task differently.", "学生对这项任务的理解不同。"),
    ("reluctant", "/rɪˈlʌktənt/", "adj. 不情愿的；勉强的", "She was reluctant to admit the mistake.", "她不愿承认这个错误。"),
    ("subsequent", "/ˈsʌbsɪkwənt/", "adj. 随后的；接着的", "Subsequent studies confirmed the result.", "后续研究证实了这一结果。"),
    ("trivial", "/ˈtrɪviəl/", "adj. 琐碎的；不重要的", "Do not waste time on trivial details.", "别在细枝末节上浪费时间。"),
    ("undermine", "/ˌʌndəˈmaɪn/", "v. 削弱；暗中破坏", "Constant criticism undermined his confidence.", "不断的批评削弱了他的信心。"),
    ("vulnerable", "/ˈvʌlnərəbl/", "adj. 易受伤害的；脆弱的", "The system is vulnerable to attack.", "这个系统容易受到攻击。"),
]

WORDS_B = [
    ("allocate", "/ˈæləkeɪt/", "v. 分配；拨给", "The school allocated funds for labs.", "学校为实验室拨款。"),
    ("bond", "/bɒnd/", "n. 纽带；债券", "A strong bond formed between them.", "他们之间形成了牢固的纽带。"),
    ("cite", "/saɪt/", "v. 引用；引证", "Remember to cite your sources.", "记得注明资料来源。"),
    ("decline", "/dɪˈklaɪn/", "v. 下降；婉拒", "Sales declined sharply last quarter.", "上季度销量大幅下降。"),
    ("emerge", "/ɪˈmɜːdʒ/", "v. 出现；浮现", "A new pattern began to emerge.", "一种新的规律开始显现。"),
    ("fundamental", "/ˌfʌndəˈmentl/", "adj. 根本的；基础的", "This is a fundamental misunderstanding.", "这是一个根本性的误解。"),
    ("generate", "/ˈdʒenəreɪt/", "v. 产生；生成", "The debate generated little interest.", "这场辩论没引起多少兴趣。"),
    ("highlight", "/ˈhaɪlaɪt/", "v. 强调；突出", "The report highlights three risks.", "报告强调了三个风险。"),
    ("imply", "/ɪmˈplaɪ/", "v. 暗示；意味着", "I did not mean to imply that.", "我不是想暗示那一点。"),
    ("justify", "/ˈdʒʌstɪfaɪ/", "v. 证明…正当；为…辩护", "Nothing can justify such a decision.", "这样的决定无论如何都说不过去。"),
    ("maintain", "/meɪnˈteɪn/", "v. 维持；坚持认为", "He maintained that he was right.", "他坚持认为自己是对的。"),
    ("obtain", "/əbˈteɪn/", "v. 获得；得到", "You must obtain written permission.", "你必须取得书面许可。"),
]

POSTS = [
    {
        "key": "p1",
        "author": "zhouzhixia",
        "type": "ask",
        "title": "这道极限题为什么不能直接洛必达？",
        "content": "lim(x→0) (x − sin x) / x³，我连洛必达三次算出来是 1/6，但老师说这里先看等价无穷小更稳。\n\n两种方法适用的边界到底在哪？是不是只有「0/0 且导数更简单」的时候才该用洛必达？",
        "subject": "高等数学",
        "topics": ["求讲解", "极限"],
        "hours_ago": 1,
        "like": 23,
        "collect": 4,
    },
    {
        "key": "p2",
        "author": "linyizhou",
        "type": "mistake",
        "title": "线代：为什么相似矩阵的迹一定相等",
        "content": "课上记了结论但没记理由，回头重做的时候又卡在第一步。",
        "subject": "线性代数",
        "topics": ["已掌握"],
        "hours_ago": 3,
        "like": 41,
        "collect": 9,
        "status": "adopted",
    },
    {
        "key": "p3",
        "author": "chenjianshan",
        "type": "material",
        "title": "大学物理期末复习提纲（含公式速查表）",
        "content": "按力学、电磁、光学三块重排了章节，公式单独做了速查页，打印出来只有四页。",
        "subject": "大学物理",
        "topics": ["期末复习"],
        "hours_ago": 5,
        "like": 128,
        "collect": 33,
    },
    {
        "key": "p4",
        "author": "shenyiran",
        "type": "paper",
        "title": "2023 秋 大学英语四级真题（第一套）",
        "content": "含答案解析，听力音频单独放在资料区了。",
        "subject": "四级",
        "topics": ["真题", "2023 秋"],
        "hours_ago": 7,
        "like": 203,
        "collect": 51,
    },
    {
        "key": "p5",
        "author": "xuzhiwei",
        "type": "ask",
        "title": "TCP 三次握手，为什么不能是两次？",
        "content": "课本上说「防止已失效的连接请求突然又传到服务端」，但我没想出一个具体会出问题的场景。",
        "subject": "计算机网络",
        "topics": ["概念", "面试"],
        "hours_ago": 26,
        "like": 62,
        "collect": 12,
        "status": "adopted",
    },
]

ANSWERS = [
    (
        "p1",
        "chenjianshan",
        "洛必达不是不能用，是这里用了会越算越复杂。sin x 展开到三阶是 x − x³/6，代进去直接得 1/6，一步就出来了。\n\n判断标准其实很简单：求导之后表达式有没有变简单。变复杂了就换等价无穷小。",
        True,
        41,
    ),
    ("p1", "xuzhiwei", "补一句：等价无穷小只能整体替换乘除里的因子，加减里直接换会出错。这题能换是因为分子整体可以展开。", False, 12),
    (
        "p2",
        "chenjianshan",
        "给个更快的路子：A 与 B 相似意味着存在可逆 P 使 B=P⁻¹AP，两边取迹，再用 tr(XY)=tr(YX) 一步就完，不用碰特征多项式。",
        True,
        18,
    ),
    (
        "p5",
        "linyizhou",
        "关键在于那个「已失效的连接请求」还留在网络里。客户端很久以前发的 SYN 因为路由问题延迟到达，服务端以为是新连接，回了 SYN-ACK 并分配资源；如果只有两次握手，服务端此刻就认为连接建立、开始等数据，而客户端早就不认这个连接了，这批资源就白占着。\n\n第三次握手的实际作用是让服务端确认「客户端还在、并且认这条连接」。",
        True,
        27,
    ),
    ("p2", "zhouzhixia", "我当时的记法是「相似的矩阵是同一个线性变换在不同基下的矩阵」。既然是同一个变换，它的不变量就都一样，迹是其中之一，所以相等。", False, 6),
]

COMMENTS = [
    ("p1", "xuzhiwei", "这段「求导变复杂就换」总结得好，我贴在笔记里了。"),
    ("p1", "zhouzhixia", "谢谢！我按这个思路又算了一遍，确实是 1/6。"),
    ("p2", "zhouzhixia", "tr(XY)=tr(YX) 这个恒等式太好用了，我老是忘记可以这么绕。"),
    ("p5", "xuzhiwei", "明白了，是「资源被占着但对方不认」这个角度，谢谢！"),
]

MISTAKES = [
    ("相似矩阵的迹一定相等", "线性代数", "特征多项式展开漏常数项", "用 tr(P⁻¹AP)=tr(A) 直接说明", 2, 2),
    ("电势叠加时积分路径的选取", "大学物理", "把参考点默认为无穷远，但题目要求取球心", "", 0, 4),
    ("B 树删除后的节点合并顺序", "数据结构", "先合并再借位，实际应先看兄弟节点", "", 1, 6),
    ("条件期望的迭代法则", "概率论", "混淆了 E[E[X|Y]] 与 E[X|Y] 的含义", "双重期望等于小 σ-代数上的条件期望", 2, 8),
]

NOTICES = [
    ("answer", "chenjianshan", "post", 2, "回答了你的问题：线代：为什么相似矩阵的迹一定相等", False, 2),
    ("adopt", "xuzhiwei", "post", 5, "采纳了你在《TCP 三次握手，为什么不能是两次？》下的回答", False, 26),
    ("comment", "zhouzhixia", "post", 2, "评论了你的内容：tr(XY)=tr(YX) 这个恒等式太好用了", False, 3),
    ("system", None, "system", None, "本周学习报告已生成：复习 96 词 · 打卡 6 天", True, 48),
]


def seed(force: bool = False) -> None:
    app = create_app()
    with app.app_context():
        if force:
            # 只清数据、不动表结构，避免把 alembic_version 一起删掉导致迁移状态丢失
            for table in reversed(db.metadata.sorted_tables):
                db.session.execute(table.delete())
            db.session.commit()
            # 自增 ID 归零，让演示数据的 id 从 1 开始，方便文档里引用
            for table in db.metadata.sorted_tables:
                try:
                    db.session.execute(db.text(f"ALTER TABLE {table.name} AUTO_INCREMENT = 1"))
                except Exception:
                    db.session.rollback()
            db.session.commit()
            print("已清空全部业务数据（表结构保留）")
        elif User.query.count() > 0:
            print("库里已有数据，跳过（需要重灌请加 --force）")
            return

        now = utcnow()
        users: dict[str, User] = {}
        for username, nickname, dept, grade, school, bio in USERS:
            user = User(
                username=username,
                nickname=nickname,
                dept=dept,
                grade=grade,
                school=school,
                bio=bio,
                avatar="",
                created_at=now - timedelta(days=30),
                updated_at=now - timedelta(days=30),
            )
            user.set_password(PASSWORD)
            db.session.add(user)
            users[username] = user
        db.session.flush()

        # ---- 帖子 ----
        posts: dict[str, Post] = {}
        for item in POSTS:
            author = users[item["author"]]
            created = now - timedelta(hours=item["hours_ago"])
            post = Post(
                type=item["type"],
                title=item["title"],
                content=item["content"],
                images=[],
                subject=item["subject"],
                topics=item["topics"],
                visibility="public",
                status=item.get("status", "pending"),
                user_id=author.id,
                like_count=item["like"],
                collect_count=item["collect"],
                answer_count=0,
                view_count=item["like"] * 3 + 20,
                created_at=created,
                updated_at=created,
            )
            db.session.add(post)
            db.session.flush()
            posts[item["key"]] = post

        # ---- 回答 ----
        for idx, (post_key, username, content, adopted, likes) in enumerate(ANSWERS):
            post = posts[post_key]
            created = post.created_at + timedelta(minutes=25 + idx * 8)
            db.session.add(
                Answer(
                    post_id=post.id,
                    user_id=users[username].id,
                    content=content,
                    images=[],
                    is_adopted=adopted,
                    like_count=likes,
                    created_at=created,
                    updated_at=created,
                )
            )
            post.answer_count += 1
            if adopted:
                users[username].adopted_count += 1

        # ---- 评论 ----
        for idx, (post_key, username, content) in enumerate(COMMENTS):
            post = posts[post_key]
            created = post.created_at + timedelta(minutes=40 + idx * 6)
            db.session.add(
                Comment(
                    target_type="post",
                    target_id=post.id,
                    user_id=users[username].id,
                    content=content,
                    created_at=created,
                    updated_at=created,
                )
            )

        # ---- 词书与词条 ----
        owner = users["linyizhou"]
        book_a = Wordbook(
            user_id=owner.id,
            name="考研英语核心词汇",
            description="从 PDF 词汇手册导入，按出现频次重排",
            source="pdf",
            color="#1F8A6B",
            total_count=len(WORDS_A),
            created_at=now - timedelta(days=9),
        )
        book_b = Wordbook(
            user_id=owner.id,
            name="四级高频词 第一组",
            description="按真题词频筛出的 12 个高频词",
            source="recommend",
            color="#3F6FB5",
            total_count=len(WORDS_B),
            created_at=now - timedelta(days=4),
        )
        db.session.add_all([book_a, book_b])
        db.session.flush()

        mastered = 0
        for i, (word, phonetic, meaning, example, _trans) in enumerate(WORDS_A):
            if i < 6:
                status, next_review, count = "mastered", now + timedelta(days=7), 3
                mastered += 1
            elif i < 16:
                status, next_review, count = "learning", now - timedelta(hours=2), 1
            else:
                status, next_review, count = "new", None, 0
            db.session.add(
                WordEntry(
                    wordbook_id=book_a.id,
                    word=word,
                    phonetic=phonetic,
                    meaning=meaning,
                    example=example,
                    confidence=0.92,
                    status=status,
                    review_count=count,
                    next_review_at=next_review,
                )
            )
        book_a.mastered_count = mastered

        for i, (word, phonetic, meaning, example, _trans) in enumerate(WORDS_B):
            db.session.add(
                WordEntry(
                    wordbook_id=book_b.id,
                    word=word,
                    phonetic=phonetic,
                    meaning=meaning,
                    example=example,
                    confidence=0.88,
                    status="new" if i > 3 else "learning",
                    review_count=0 if i > 3 else 1,
                    next_review_at=None if i > 3 else now - timedelta(hours=1),
                )
            )

        # ---- 错题 ----
        for prompt, subject, reason, answer, mastery, days_ago in MISTAKES:
            created = now - timedelta(days=days_ago)
            db.session.add(
                Mistake(
                    user_id=owner.id,
                    prompt=prompt,
                    knowledge_point=subject,
                    reason=reason,
                    answer=answer,
                    mastery=mastery,
                    created_at=created,
                    updated_at=created,
                )
            )

        # ---- 计划 ----
        db.session.add(
            Plan(
                user_id=owner.id,
                name="考研词汇冲刺",
                target_type="words",
                target_value=24,
                period="daily",
                deadline=(date.today() + timedelta(days=18)),
                progress=8,
                ref_type="wordbook",
                ref_id=book_a.id,
            )
        )

        # ---- 连续 6 天打卡（今天留给用户自己打） ----
        for i in range(6, 0, -1):
            day = date.today() - timedelta(days=i)
            db.session.add(
                Checkin(
                    user_id=owner.id,
                    date=day,
                    word_count=20 + (i % 3) * 4,
                    streak_snapshot=7 - i,
                    created_at=datetime.combine(day, datetime.min.time()) + timedelta(hours=21),
                )
            )
        owner.streak_days = 6
        owner.total_checkin_days = 6

        # ---- 通知 ----
        for notice_type, actor_username, target_type, target_id, summary, is_read, hours_ago in NOTICES:
            created = now - timedelta(hours=hours_ago)
            db.session.add(
                Notification(
                    recipient_id=owner.id,
                    type=notice_type,
                    actor_id=users[actor_username].id if actor_username else None,
                    target_type=target_type,
                    target_id=posts["p2"].id if target_id == 2 and target_type == "post" else (
                        posts["p5"].id if target_id == 5 and target_type == "post" else target_id
                    ),
                    summary=summary,
                    is_read=is_read,
                    created_at=created,
                    updated_at=created,
                )
            )

        db.session.commit()
        print("演示数据写入完成")
        print(f"登录账号：linyizhou / {PASSWORD}（其余演示账号密码相同）")


if __name__ == "__main__":
    seed(force="--force" in sys.argv)
