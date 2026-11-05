# Rainforest tree generator

Vendored from https://github.com/Ben-Edwards44/PyBonsai at 4e6546e6953f86b6a0494a85fd22714f11dc0e40.
Copyright 2024 Ben Edwards; MIT license included in pybonsai/LICENSE.
Sibling imports were changed to relative imports; trailing whitespace was removed.

terminal-rainforest uses RandomOffsetFibTree directly, without the pot or cursor
animation. A fixed canvas adapter maps its branch and foliage colors to terminal
palette slots and combines closely spaced trees into a full-width forest.
Python standard library only; no runtime download or pip install.
