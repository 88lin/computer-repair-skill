/* ============================================================================
   运行时用得上的界面字符串——筛选条、计数、复制提示和详情弹窗的字段名。

   页面正文的英文译文不在这里：/ 和 /en/ 是两个静态页面，正文在构建期就翻译好了，
   浏览器不需要再下载一份字典。正文译文放在 tools/i18n_en.json，
   由 tools/build_site.py 读取。
   ========================================================================= */
window.CRS_I18N = {

ui: {
  zh: {
    all:         "全部",
    clear:       "清空",
    count:       "显示 {n} / {t} 条",
    copied:      "已复制",
    copyFail:    "复制失败，请手动选择文本",
    mTriggers:   "触发症状",
    mPrompt:     "示例提问",
    mWhen:       "何时启用",
    mPlatform:   "平台",
    mReviewed:   "最后审阅",
    mFile:       "源文件",
    catAria:     "按分类筛选：",
    platAria:    "按平台筛选：",
    rowAria:     "查看详情："
  },
  en: {
    all:         "All",
    clear:       "Clear",
    count:       "Showing {n} of {t}",
    copied:      "Copied",
    copyFail:    "Copy failed — please select the text manually",
    mTriggers:   "Triggers",
    mPrompt:     "Sample prompt",
    mWhen:       "When to activate",
    mPlatform:   "Platform",
    mReviewed:   "Last reviewed",
    mFile:       "Source file",
    catAria:     "Filter by category: ",
    platAria:    "Filter by platform: ",
    rowAria:     "View details: "
  }
}

};
