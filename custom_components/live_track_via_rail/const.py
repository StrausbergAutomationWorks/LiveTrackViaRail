"""Constants for Live Track VIA Rail."""

DOMAIN = "live_track_via_rail"

# The Amtraker provider this integration filters on. The three providers do
# NOT share a data contract -- see 05_SHARED_LESSONS.md B8.4 -- which is why
# they are three integrations rather than one with an option.
PROVIDER = "Via"

# ODC-By v1.0 requires attribution. This rides on the ENTITY, so it travels
# onto any dashboard card the user builds, including the shared map.
ATTRIBUTION = "Data from Amtraker (amtraker.com), ODC-By v1.0"

# Identifies this project to the upstream server, which BLOCKS requests that
# carry no User-Agent.
USER_AGENT = "LiveTrackVIARail/0.1.0 (+https://github.com/StrausbergAutomationWorks/LiveTrackViaRail)"
