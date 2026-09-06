use anyhow::{anyhow, Result};
use matrix_sdk::{config::SyncSettings, ruma::RoomId, Client};
use serde_json::Value;

pub const MUSITU_MATRIX_EVENT_TYPE: &str = "org.musitu.continuum.envelope.v1";

/// Matrix carries the MUSITU envelope as the exact custom-event content object.
/// Matrix room/event identifiers remain transport metadata and never enter the
/// universal envelope itself.
pub fn matrix_event_content(envelope: Value) -> Value {
    envelope
}

pub struct MatrixTransport {
    client: Client,
}

impl MatrixTransport {
    pub fn from_client(client: Client) -> Self {
        Self { client }
    }

    pub async fn login(homeserver_url: &str, username: &str, password: &str) -> Result<Self> {
        let client = Client::builder()
            .homeserver_url(homeserver_url)
            .build()
            .await?;

        client
            .matrix_auth()
            .login_username(username, password)
            .initial_device_display_name("MUSITU Continuum")
            .send()
            .await?;

        client.sync_once(SyncSettings::default()).await?;

        Ok(Self { client })
    }

    pub async fn send_envelope(&self, room_id: &RoomId, envelope: Value) -> Result<()> {
        let room = self
            .client
            .get_room(room_id)
            .ok_or_else(|| anyhow!("Matrix room is not present in client state: {room_id}"))?;

        room.send_raw(MUSITU_MATRIX_EVENT_TYPE, matrix_event_content(envelope))
            .await?;
        Ok(())
    }
}
