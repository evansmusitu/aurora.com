use matrix_sdk::ruma::RoomId;
use musitu_matrix_transport::MatrixTransport;
use serde_json::json;
use std::env;

#[tokio::test(flavor = "multi_thread")]
async fn sends_exact_musitu_envelope_through_live_homeserver() {
    if env::var("MUSITU_MATRIX_LIVE").as_deref() != Ok("1") {
        return;
    }

    let homeserver = env::var("MUSITU_MATRIX_HOMESERVER").expect("MUSITU_MATRIX_HOMESERVER");
    let username = env::var("MUSITU_MATRIX_USERNAME").expect("MUSITU_MATRIX_USERNAME");
    let password = env::var("MUSITU_MATRIX_PASSWORD").expect("MUSITU_MATRIX_PASSWORD");
    let room_id = env::var("MUSITU_MATRIX_ROOM_ID").expect("MUSITU_MATRIX_ROOM_ID");

    let transport = MatrixTransport::login(&homeserver, &username, &password)
        .await
        .expect("Matrix login");
    let room_id = RoomId::parse(room_id).expect("valid Matrix room id");

    let envelope = json!({
        "version": "musitu-envelope/1",
        "message_id": "msg_live_matrix_ci",
        "conversation_id": "conv_live_matrix_ci",
        "sender_musitu_id": "musitu_sender_ci",
        "recipient_musitu_ids": ["musitu_recipient_ci"],
        "created_at": "2026-09-04T16:35:00+00:00",
        "content_type": "text/plain",
        "priority": "normal",
        "payload_b64": "bGl2ZS1tYXRyaXg=",
        "payload_sha256": "6606ba6d96b8831a10cb46349c0ea9af1477fb0568c54e6fd81e6e2cb7dcbf49"
    });

    transport
        .send_envelope(&room_id, envelope)
        .await
        .expect("send MUSITU envelope through Matrix");
}
