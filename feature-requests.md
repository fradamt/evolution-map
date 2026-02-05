# Feature Requests

- [x] When you click on a node (and the sidebar opens), the view should stay fixed as if you were hovering on it, i.e. the arrows out of it should be highlighted, the dependent nodes should stay highlighted etc... So you can move the cursor away from the node and go explore the dependencies
- [x] When you click on a node and hover over a link in "References" (in the sidebar that opens for the node), the corresponding node should be highlighted
- [x] When you click on a link in References and the sidebar switches to the new node (the one referenced in the link), the corresponding node should now be the one "in focus" (same concept as 1)

# Issues

- [x] LMD GHOST with ~256 validators and a fast-following finality gadget is very relevant to the Single Slot finality category. Generally the issue is with the category itself, it shouldn't be so much about "Single Slot Finality" but Consensus evolution. Perhaps it should just be merged with the first category, except it should be called Proof of Stake and Consensus, not Casper. Or perhaps there should be a Consensus category
  - **Fixed**: Merged SSF thread into "Consensus & Finality" (87 topics). Added SSF/LMD-GHOST/fork-choice patterns.
- [x] Some other things are in Other that shouldn't, like FullDAS, this is about DAS. Or the big blocks analysis
  - **Fixed**: Added fulldas/peerdas/big-block/blob-count patterns to Sharding & DA (90 topics, up from 79).
- [x] In general the categorization is not quite working
  - **Fixed**: Broadened title patterns for all 11 threads, lowered match threshold from 1.5 to 1.0. Unassigned dropped from 183 to 121.
- [x] Not able to nicely scroll left to right anymore
  - **Fixed**: Changed zoom behavior — wheel/trackpad scrolls horizontally, ctrl+wheel/pinch zooms, double-click resets.
