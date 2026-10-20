/**
 * 广场 mock 数据。
 * 无后端时作为 loadFeed 的默认数据源；接入真实接口后删除本文件即可。
 * 字段对齐 Spec 第 6 章 Post 实体。
 */

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;

const now = Date.now();

const POSTS = [
  {
    id: 'p1001',
    category: '求助',
    title: '这道高数极限题为什么不能直接用洛必达？',
    excerpt: '算到这里总觉得少了一步，尝试了两种方法答案都不一样，求指点一下思路～',
    author: { id: 'u11', nickname: '周知夏', dept: '数学系', avatarText: '周' },
    images: [{ url: '', ratio: 1.78 }],
    tags: ['高等数学', '求讲解', '极限'],
    answers: 8,
    likes: 23,
    collects: 6,
    liked: false,
    collected: false,
    createdAt: now - 12 * MINUTE
  },
  {
    id: 'p1002',
    category: '错题',
    title: '线代：为什么相似矩阵的迹一定相等',
    excerpt: '错因是把特征多项式展开时漏掉了常数项，整理一下正确的推导。',
    author: { id: 'u12', nickname: '林一舟', dept: '计算机系', avatarText: '林' },
    images: [],
    tags: ['线性代数', '已掌握'],
    answers: 3,
    likes: 41,
    collects: 12,
    liked: true,
    collected: true,
    createdAt: now - 2 * HOUR
  },
  {
    id: 'p1003',
    category: '资料',
    title: '大学物理期末复习提纲（含公式速查表）',
    excerpt: '整理了三学期的重点章节，公式按模块归类，打印出来只有四页。',
    author: { id: 'u13', nickname: '陈见山', dept: '物理系', avatarText: '陈' },
    images: [],
    file: { name: '大学物理复习提纲.pdf', pages: 12, size: '2.4 MB' },
    tags: ['大学物理', '期末复习'],
    answers: 0,
    likes: 128,
    collects: 96,
    liked: false,
    collected: false,
    createdAt: now - 5 * HOUR
  },
  {
    id: 'p1004',
    category: '试卷',
    title: '2024 秋 数据结构期中真题（含参考答案）',
    excerpt: '去年期中卷，题型和今年大纲基本一致，最后两道大题值得反复做。',
    author: { id: 'u14', nickname: '苏晚', dept: '计算机系', avatarText: '苏' },
    images: [],
    file: { name: '数据结构期中2024.pdf', pages: 8, size: '1.1 MB' },
    tags: ['数据结构', '2024 秋'],
    answers: 0,
    likes: 302,
    collects: 210,
    liked: false,
    collected: false,
    createdAt: now - 26 * HOUR
  },
  {
    id: 'p1005',
    category: '求助',
    title: '英语长难句划分总出错，有没有系统的练习方法？',
    excerpt: '从句一多就找不到主谓，想知道大家是怎么练的。',
    author: { id: 'u15', nickname: '何知微', dept: '外国语学院', avatarText: '何' },
    images: [],
    tags: ['英语', '长难句', '求经验'],
    answers: 15,
    likes: 67,
    collects: 33,
    liked: false,
    collected: false,
    createdAt: now - 3 * 24 * HOUR
  },
  {
    id: 'p1006',
    category: '资料',
    title: '概率论与数理统计 手写笔记合集',
    excerpt: '按章节整理，重点公式用红笔标注，附三套自测题。',
    author: { id: 'u16', nickname: '许南', dept: '统计系', avatarText: '许' },
    images: [],
    file: { name: '概率论笔记合集.pdf', pages: 34, size: '8.7 MB' },
    tags: ['概率论', '笔记'],
    answers: 0,
    likes: 88,
    collects: 74,
    liked: false,
    collected: false,
    createdAt: now - 4 * 24 * HOUR
  }
];

/**
 * 按分类取列表。推荐返回全量，其余按 category 精确匹配。
 */
function query(category) {
  if (!category || category === '推荐') return POSTS.slice();
  return POSTS.filter((post) => post.category === category);
}

module.exports = { query, POSTS };
