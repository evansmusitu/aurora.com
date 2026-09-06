use musitu_matrix_transport::{matrix_event_content, MUSITU_MATRIX_EVENT_TYPE};
use serde_json::json;

#[test]
fn uses_musitu_custom_event_type_and_preserves_envelope_exactly() {
    let envelope = json!({
        "version": "musitu-envelope/1",
        "message_id": "msg_123",
        "conversation_id": "conv_123",
        "sender_musitu_id": "musitu_sender",
        "recipient_musitu_ids": ["musitu_recipient"],
        "created_at": "2026-09-04T15:00:00+00:00",
        "content_type": "text/plain",
        "priority": "normal",
        "payload_b64": "aGVsbG8=",
        "payload_sha256": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    });

    assert_eq!(MUSITU_MATRIX_EVENT_TYPE, "org.musitu.continuum.envelope.v1");
    assert_eq!(matrix_event_content(envelope.clone()), envelope);
}
