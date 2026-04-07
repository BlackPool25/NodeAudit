# GraphReview Report

## Executive Summary
- Source root: /home/lightdesk/Downloads/Projects/NodeAudit/code-review-env/sample_project
- Episode id: all
- Modules in scope: 60
- Confidence score: 0.100
- Precision: 0.000 | Recall: 0.000 | F1: 0.000
- Security coverage: 0.000 | Dependency attribution validity: 0.000

## Security Analysis
### config
- [LOW] B105 line 6: Possible hardcoded password: 'hardcoded-dev-key'

### payments
- [LOW] B404 line 3: Consider possible security implications associated with the subprocess module.
- [HIGH] B602 line 9: subprocess call with shell=True identified, security issue.

## Cascade Attribution Summary
## Module Reviews
### auth
- Status: pending
- Summary: exports: [issue_session_token(user_id: str)->str] | issues: 2 | depends_on: [config]
- Shape: functions=issue_session_token
- Findings: 2
- Reviews: 0

### cart
- Status: pending
- Summary: exports: [calculate_subtotal(items: list[dict[str, float]])->float, calculate_total(items: list[dict[str, float]])->float] | issues: 2 | depends_on: [config]
- Shape: functions=calculate_subtotal, calculate_total
- Findings: 2
- Reviews: 0

### checkout
- Status: pending
- Summary: exports: [submit_order(items: list[dict[str, float]])->str] | issues: 1 | depends_on: [cart, payments]
- Shape: functions=submit_order
- Findings: 1
- Reviews: 0

### config
- Status: pending
- Summary: exports: [] | issues: 1 | depends_on: []
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 1
- Reviews: 0

### database
- Status: pending
- Summary: exports: [get_connection_url()->str] | issues: 3 | depends_on: [config, config.SETTINGS]
- Shape: functions=get_connection_url
- Findings: 3
- Reviews: 0

### huge_module
- Status: pending
- Summary: exports: [bootstrap()->int, helper_alpha()->int, helper_beta()->int, run(self)->int, auto_func_1()->int] | issues: 51 | depends_on: []
- Shape: No top-level functions/classes; likely constants, helpers, or script-style module.
- Findings: 51
- Reviews: 0

### huge_module::GiantService
- Status: pending
- Summary: Chunk GiantService lines 446-448
- Shape: classes=GiantService
- Findings: 0
- Reviews: 0

### huge_module::auto_func_1
- Status: pending
- Summary: Chunk auto_func_1 lines 451-452
- Shape: functions=auto_func_1
- Findings: 0
- Reviews: 0

### huge_module::auto_func_10
- Status: pending
- Summary: Chunk auto_func_10 lines 487-488
- Shape: functions=auto_func_10
- Findings: 0
- Reviews: 0

### huge_module::auto_func_11
- Status: pending
- Summary: Chunk auto_func_11 lines 491-492
- Shape: functions=auto_func_11
- Findings: 0
- Reviews: 0

### huge_module::auto_func_12
- Status: pending
- Summary: Chunk auto_func_12 lines 495-496
- Shape: functions=auto_func_12
- Findings: 0
- Reviews: 0

### huge_module::auto_func_13
- Status: pending
- Summary: Chunk auto_func_13 lines 499-500
- Shape: functions=auto_func_13
- Findings: 0
- Reviews: 0

### huge_module::auto_func_14
- Status: pending
- Summary: Chunk auto_func_14 lines 503-504
- Shape: functions=auto_func_14
- Findings: 0
- Reviews: 0

### huge_module::auto_func_15
- Status: pending
- Summary: Chunk auto_func_15 lines 507-508
- Shape: functions=auto_func_15
- Findings: 0
- Reviews: 0

### huge_module::auto_func_16
- Status: pending
- Summary: Chunk auto_func_16 lines 511-512
- Shape: functions=auto_func_16
- Findings: 0
- Reviews: 0

### huge_module::auto_func_17
- Status: pending
- Summary: Chunk auto_func_17 lines 515-516
- Shape: functions=auto_func_17
- Findings: 0
- Reviews: 0

### huge_module::auto_func_18
- Status: pending
- Summary: Chunk auto_func_18 lines 519-520
- Shape: functions=auto_func_18
- Findings: 0
- Reviews: 0

### huge_module::auto_func_19
- Status: pending
- Summary: Chunk auto_func_19 lines 523-524
- Shape: functions=auto_func_19
- Findings: 0
- Reviews: 0

### huge_module::auto_func_2
- Status: pending
- Summary: Chunk auto_func_2 lines 455-456
- Shape: functions=auto_func_2
- Findings: 0
- Reviews: 0

### huge_module::auto_func_20
- Status: pending
- Summary: Chunk auto_func_20 lines 527-528
- Shape: functions=auto_func_20
- Findings: 0
- Reviews: 0

### huge_module::auto_func_21
- Status: pending
- Summary: Chunk auto_func_21 lines 531-532
- Shape: functions=auto_func_21
- Findings: 0
- Reviews: 0

### huge_module::auto_func_22
- Status: pending
- Summary: Chunk auto_func_22 lines 535-536
- Shape: functions=auto_func_22
- Findings: 0
- Reviews: 0

### huge_module::auto_func_23
- Status: pending
- Summary: Chunk auto_func_23 lines 539-540
- Shape: functions=auto_func_23
- Findings: 0
- Reviews: 0

### huge_module::auto_func_24
- Status: pending
- Summary: Chunk auto_func_24 lines 543-544
- Shape: functions=auto_func_24
- Findings: 0
- Reviews: 0

### huge_module::auto_func_25
- Status: pending
- Summary: Chunk auto_func_25 lines 547-548
- Shape: functions=auto_func_25
- Findings: 0
- Reviews: 0

### huge_module::auto_func_26
- Status: pending
- Summary: Chunk auto_func_26 lines 551-552
- Shape: functions=auto_func_26
- Findings: 0
- Reviews: 0

### huge_module::auto_func_27
- Status: pending
- Summary: Chunk auto_func_27 lines 555-556
- Shape: functions=auto_func_27
- Findings: 0
- Reviews: 0

### huge_module::auto_func_28
- Status: pending
- Summary: Chunk auto_func_28 lines 559-560
- Shape: functions=auto_func_28
- Findings: 0
- Reviews: 0

### huge_module::auto_func_29
- Status: pending
- Summary: Chunk auto_func_29 lines 563-564
- Shape: functions=auto_func_29
- Findings: 0
- Reviews: 0

### huge_module::auto_func_3
- Status: pending
- Summary: Chunk auto_func_3 lines 459-460
- Shape: functions=auto_func_3
- Findings: 0
- Reviews: 0

### huge_module::auto_func_30
- Status: pending
- Summary: Chunk auto_func_30 lines 567-568
- Shape: functions=auto_func_30
- Findings: 0
- Reviews: 0

### huge_module::auto_func_31
- Status: pending
- Summary: Chunk auto_func_31 lines 571-572
- Shape: functions=auto_func_31
- Findings: 0
- Reviews: 0

### huge_module::auto_func_32
- Status: pending
- Summary: Chunk auto_func_32 lines 575-576
- Shape: functions=auto_func_32
- Findings: 0
- Reviews: 0

### huge_module::auto_func_33
- Status: pending
- Summary: Chunk auto_func_33 lines 579-580
- Shape: functions=auto_func_33
- Findings: 0
- Reviews: 0

### huge_module::auto_func_34
- Status: pending
- Summary: Chunk auto_func_34 lines 583-584
- Shape: functions=auto_func_34
- Findings: 0
- Reviews: 0

### huge_module::auto_func_35
- Status: pending
- Summary: Chunk auto_func_35 lines 587-588
- Shape: functions=auto_func_35
- Findings: 0
- Reviews: 0

### huge_module::auto_func_36
- Status: pending
- Summary: Chunk auto_func_36 lines 591-592
- Shape: functions=auto_func_36
- Findings: 0
- Reviews: 0

### huge_module::auto_func_37
- Status: pending
- Summary: Chunk auto_func_37 lines 595-596
- Shape: functions=auto_func_37
- Findings: 0
- Reviews: 0

### huge_module::auto_func_38
- Status: pending
- Summary: Chunk auto_func_38 lines 599-600
- Shape: functions=auto_func_38
- Findings: 0
- Reviews: 0

### huge_module::auto_func_39
- Status: pending
- Summary: Chunk auto_func_39 lines 603-604
- Shape: functions=auto_func_39
- Findings: 0
- Reviews: 0

### huge_module::auto_func_4
- Status: pending
- Summary: Chunk auto_func_4 lines 463-464
- Shape: functions=auto_func_4
- Findings: 0
- Reviews: 0

### huge_module::auto_func_40
- Status: pending
- Summary: Chunk auto_func_40 lines 607-608
- Shape: functions=auto_func_40
- Findings: 0
- Reviews: 0

### huge_module::auto_func_41
- Status: pending
- Summary: Chunk auto_func_41 lines 611-612
- Shape: functions=auto_func_41
- Findings: 0
- Reviews: 0

### huge_module::auto_func_42
- Status: pending
- Summary: Chunk auto_func_42 lines 615-616
- Shape: functions=auto_func_42
- Findings: 0
- Reviews: 0

### huge_module::auto_func_43
- Status: pending
- Summary: Chunk auto_func_43 lines 619-620
- Shape: functions=auto_func_43
- Findings: 0
- Reviews: 0

### huge_module::auto_func_44
- Status: pending
- Summary: Chunk auto_func_44 lines 623-624
- Shape: functions=auto_func_44
- Findings: 0
- Reviews: 0

### huge_module::auto_func_45
- Status: pending
- Summary: Chunk auto_func_45 lines 627-628
- Shape: functions=auto_func_45
- Findings: 0
- Reviews: 0

### huge_module::auto_func_5
- Status: pending
- Summary: Chunk auto_func_5 lines 467-468
- Shape: functions=auto_func_5
- Findings: 0
- Reviews: 0

### huge_module::auto_func_6
- Status: pending
- Summary: Chunk auto_func_6 lines 471-472
- Shape: functions=auto_func_6
- Findings: 0
- Reviews: 0

### huge_module::auto_func_7
- Status: pending
- Summary: Chunk auto_func_7 lines 475-476
- Shape: functions=auto_func_7
- Findings: 0
- Reviews: 0

### huge_module::auto_func_8
- Status: pending
- Summary: Chunk auto_func_8 lines 479-480
- Shape: functions=auto_func_8
- Findings: 0
- Reviews: 0

### huge_module::auto_func_9
- Status: pending
- Summary: Chunk auto_func_9 lines 483-484
- Shape: functions=auto_func_9
- Findings: 0
- Reviews: 0

### huge_module::bootstrap
- Status: pending
- Summary: Chunk bootstrap lines 4-5
- Shape: functions=bootstrap
- Findings: 0
- Reviews: 0

### huge_module::helper_alpha
- Status: pending
- Summary: Chunk helper_alpha lines 438-439
- Shape: functions=helper_alpha
- Findings: 0
- Reviews: 0

### huge_module::helper_beta
- Status: pending
- Summary: Chunk helper_beta lines 442-443
- Shape: functions=helper_beta
- Findings: 0
- Reviews: 0

### inventory
- Status: pending
- Summary: exports: [is_available(item_name: str)->bool] | issues: 2 | depends_on: [validators, validators.is_non_empty]
- Shape: functions=is_available
- Findings: 2
- Reviews: 0

### notifications
- Status: pending
- Summary: exports: [send_email(recipient: str, body: str)->None] | issues: 2 | depends_on: [smtplib]
- Shape: functions=send_email
- Findings: 2
- Reviews: 0

### payments
- Status: pending
- Summary: exports: [run_gateway_check(endpoint: str)->int, charge(total: float)->str] | issues: 4 | depends_on: [subprocess]
- Shape: functions=run_gateway_check, charge
- Findings: 4
- Reviews: 0

### utils
- Status: pending
- Summary: exports: [pick_item(preferred: str, fallback: str)->str] | issues: 2 | depends_on: [inventory, inventory.is_available]
- Shape: functions=pick_item
- Findings: 2
- Reviews: 0

### validators
- Status: pending
- Summary: exports: [is_non_empty(value: str | None)->bool, validate_coupon(code: str | None)->bool] | issues: 3 | depends_on: []
- Shape: functions=is_non_empty, validate_coupon
- Findings: 3
- Reviews: 0

## RL Integrity
- Trajectory reconstructable from DB annotations and episode records.
- Reward causality linked to each persisted action payload.
- Easy/Medium deterministic replay expected; Hard constrained by temperature=0 judge policy.
