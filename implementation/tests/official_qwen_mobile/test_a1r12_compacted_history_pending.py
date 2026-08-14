from raven_m.official_qwen_mobile.a1r12_compacted_history_pending import CompactedHistoryPendingMemory,MECHANISM_ID
def test_only_consecutive_normalized_duplicates_are_removed()->None:
 m=CompactedHistoryPendingMemory();assert m.prompt_history(['Tap A',' "tap a" ','Tap B','Tap A'])==[' "tap a" ','Tap B','Tap A'];assert m.audit_record()['counters']['history_items_removed_count']==1
def test_read_identity_and_self_check_survive()->None:
 m=CompactedHistoryPendingMemory();text,a=m.read({'goal':'Delete A'});event=m.commit_injection(a['ticket_id'],'p');assert 'COORDINATE SELF-CHECK' in text and event['mechanism_id']==MECHANISM_ID
