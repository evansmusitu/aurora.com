use matrix_sdk::{
    Client,
    config::SyncSettings,
    room::MessagesOptions,
    ruma::api::client::room::create_room::v3::Request as CreateRoomRequest,
};
use musitu_matrix_transport::{MUSITU_MATRIX_EVENT_TYPE, MatrixTransport};
use serde_json::{Value, json};
use std::{env, fs, path::PathBuf};

#[tokio::test(flavor = "multi_thread")]
async fn encrypts_on_server_and_recovers_musitu_envelope_for_authorized_client() {
    if env::var("MUSITU_MATRIX_E2EE_LIVE").as_deref() != Ok("1") {
        return;
    }

    let homeserver = env::var("MUSITU_MATRIX_HOMESERVER").expect("MUSITU_MATRIX_HOMESERVER");
    let username = env::var("MUSITU_MATRIX_E2EE_USERNAME").expect("MUSITU_MATRIX_E2EE_USERNAME");
    let password = env::var("MUSITU_MATRIX_E2EE_PASSWORD").expect("MUSITU_MATRIX_E2EE_PASSWORD");
    let runner_temp = PathBuf::from(env::var("RUNNER_TEMP").expect("RUNNER_TEMP"));

    let client = Client::builder()
        .homeserver_url(&homeserver)
        .build()
        .await
        .expect("build Matrix client");

    client
        .matrix_auth()
        .login_username(&username, &password)
        .initial_device_display_name("MUSITU Continuum E2EE CI")
        .send()
        .await
        .expect("Matrix E2EE login");
    client
        .sync_once(SyncSettings::default())
        .await
        .expect("initial Matrix E2EE sync");

    let room = client
        .create_room(CreateRoomRequest::new())
        .await
        .expect("create Matrix E2EE room");
    room.enable_encryption()
        .await
        .expect("enable Matrix room encryption");
    client
        .sync_once(SyncSettings::default())
        .await
        .expect("sync encrypted room state");

    fs::write(
        runner_temp.join("musitu-matrix-e2ee-room-id"),
        room.room_id().as_str(),
    )
    .expect("persist E2EE room id for raw server verification");

    let envelope = json!({
        "version": "musitu-envelope/1",
        "message_id": "msg_live_matrix_e2ee",
        "conversation_id": "conv_live_matrix_e2ee",
        "sender_musitu_id": "musitu_sender_e2ee",
        "recipient_musitu_ids": ["musitu_recipient_e2ee"],
        "created_at": "2026-09-04T17:10:00+00:00",
        "content_type": "text/plain",
        "priority": "normal",
        "payload_b64": "ZW5jcnlwdGVkLW1hdHJpeA==",
        "payload_sha256": "8ddb7899a6a906399bc132b1a80da4dd81fd996d8267181164c095a438599e9f"
    });

    let transport = MatrixTransport::from_client(client.clone());
    transport
        .send_envelope(room.room_id(), envelope.clone())
        .await
        .expect("send MUSITU envelope through encrypted Matrix room");

    client
        .sync_once(SyncSettings::default())
        .await
        .expect("sync encrypted MUSITU event");

    let messages = room
        .messages(MessagesOptions::backward())
        .await
        .expect("fetch Matrix room messages for decryption");

    let recovered = messages
        .chunk
        .iter()
        .find(|event| event.kind.event_type().as_deref() == Some(MUSITU_MATRIX_EVENT_TYPE))
        .expect("authorized Matrix client recovered MUSITU custom event type");

    assert!(
        recovered.encryption_info().is_some(),
        "recovered MUSITU event must carry successful decryption metadata"
    );

    let recovered_json: Value = serde_json::from_str(recovered.raw().json().get())
        .expect("decrypted Matrix event JSON");
    assert_eq!(recovered_json["type"], MUSITU_MATRIX_EVENT_TYPE);
    assert_eq!(recovered_json["content"], envelope);
}
