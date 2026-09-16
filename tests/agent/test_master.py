from __future__ import annotations

from app.agent.master import BlueprintRequest, MasterAgent
from app.channel.models import ChannelIdentity, ChannelSyncResult, PublicChannel, PublicVideo
from app.creative.blueprint import ProductionBlueprint
from app.intelligence.recipe_master import RecipeCandidate


class FakeSyncProvider:
    def __init__(self, channel: PublicChannel):
        self.channel = channel

    def sync(self, handle: str) -> ChannelSyncResult:
        return ChannelSyncResult(
            channel=self.channel,
            snapshot_id="snapshot-1",
            snapshot_version=1,
            new_video_ids=tuple(video.video_id for video in self.channel.videos),
            changed_video_ids=(),
            unchanged_video_ids=(),
            private_analytics_available=False,
            metadata={"public_only": True},
        )


def _channel() -> PublicChannel:
    identity = ChannelIdentity(
        channel_id="UC12345678901234567890",
        channel_handle="@demo",
        channel_url="https://www.youtube.com/@demo",
        title="Demo Channel",
    )
    return PublicChannel(
        identity=identity,
        videos=(
            PublicVideo(video_id="v1", title="Village Chutney Recipe", duration_seconds=45),
            PublicVideo(video_id="v2", title="Secret Village Curry", duration_seconds=50),
        ),
    )


def test_analyze_channel_runs_handle_first_sync_and_analysis():
    agent = MasterAgent(sync_provider=FakeSyncProvider(_channel()))

    result = agent.analyze_channel("@demo")

    assert result.channel_id == "UC12345678901234567890"
    assert result.video_count == 2
    assert result.private_analytics_available is False
    assert result.status == "observed"


def test_create_blueprint_rejects_duplicate_recipe_before_building():
    candidate = RecipeCandidate(
        name="Potato Curry",
        ingredients=("potato", "onion", "tomato"),
        cooking_method="slow simmer",
        region="Gujarat",
        story_angle="village memory",
        visual_concept="earthen pot",
        asmr_elements=("sizzle",),
    )

    class DuplicateMaster:
        def check_uniqueness(self, value):
            from app.intelligence.recipe_master import UniquenessResult

            return UniquenessResult(allowed=False, reason="semantic_duplicate")

    agent = MasterAgent(recipe_master=DuplicateMaster())
    request = BlueprintRequest(
        recipe=candidate,
        world={
            "location": "Kutch village",
            "season": "winter",
            "weather": "clear",
            "kitchen": "courtyard kitchen",
            "character": {"style": "Ghibli-inspired 2D"},
        },
        story={
            "hook": "A forgotten village recipe",
            "origin": "old village kitchen",
            "discovery": "an old spice box",
            "transformation": "slow simmer",
            "reveal": "the finished curry",
        },
        scenes=[{"beats": ["a", "b", "c"]}] * 9,
    )

    try:
        agent.create_blueprint(request)
    except ValueError as exc:
        assert "not unique" in str(exc)
    else:
        raise AssertionError("duplicate recipe must be rejected")
