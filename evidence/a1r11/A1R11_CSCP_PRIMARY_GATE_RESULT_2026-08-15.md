# A1-R11 CSCP Primary Gate Result

A1-R11 produced a valid reward-0 max-step failure on `ExpenseDeleteMultiple2` (34 calls/actions, 141,660 tokens). The exact self-check was injected 34 times and the model explicitly performed its percentage conversion on 10 decisions. It successfully deleted Public Transit, but repeated scrolling and accumulated identical history prevented deletion of Tuition Fees and Bike Repairs.

This falsifies prompt-only coordinate self-calibration as a sufficient repair. The next prospective change targets a different causal mechanism: consecutive identical action prose in ordinary history will be deterministically compressed before the request, while the raw executed-action audit remains intact. A known inherited-counter defect made the unused R10 calibration counter negative; it did not affect the exact R11 injection audit, requests, actions, reward, or stopping decision.
