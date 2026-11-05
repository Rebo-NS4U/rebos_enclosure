# Rainforest tree generator

Vendored from https://github.com/Ben-Edwards44/PyBonsai at 4e6546e6953f86b6a0494a85fd22714f11dc0e40.
Copyright 2024 Ben Edwards; MIT license included in pybonsai/LICENSE.
Sibling imports were changed to relative imports; trailing whitespace was removed.

terminal-rainforest uses RandomOffsetFibTree directly, without the pot or cursor
animation. A fixed canvas adapter maps its branch and foliage colors to terminal
palette slots and composes an overhead canopy above tall foreground trunks, distant trees,
hanging vines and fern-covered roots. Small mushrooms and sparse points of light
add detail while leaving the clearing open. The composition fills the width.
Python standard library only; no runtime download or pip install.
