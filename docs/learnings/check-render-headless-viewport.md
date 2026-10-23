# check-render 的 headless 视口测量盲区

> 2026-10-08 · 发现于 theme-proving 验收（第三轮）· 状态：已记录，待修

## 现象

`check-render.py`（Playwright headless，Chromium 145）对远屏页的测量可疑失效：deck 的程序化滚动（`scrollIntoView` 滚了 window 而非 deck 容器、`deck.scrollTo` 写了 scrollTop 但版式不动）+ `content-visibility:auto` + IntersectionObserver 不为远屏页发 in-view，三者复合。后果：

- 远屏页只测到"无动效或初始 `opacity:0` 被过滤"的元素——**测量覆盖静默残缺**；
- `mask-lines` 是唯一"可见但位移"的入场形态（`.ml-inner` 初始 `translateY(112%)`），远屏页必被误报重叠。

T18/T34 不受影响（它们显式强制 content-visibility visible + reduced-motion 终态测量）。

## 修法备查

check-render 测量前与 T18/T34 同口径：强制全部 slide-slot `content-visibility:visible` + reduced-motion 终态（或直接以 reduced-motion 测量——终态即布局真相，动效零位移）。

## 教训

验收工具本身的"测量前提失效"不会报错，只会静默测少——**测量脚本要先自证覆盖**（例如断言每页测量到的元素数 > 0 且与 DOM 计数一致），否则 PASS 可能是假绿。
