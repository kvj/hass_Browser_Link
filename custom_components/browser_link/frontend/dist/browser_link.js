
(function() {

    const indicatorDiv = document.createElement("div");
    indicatorDiv.style.zIndex = 20000;
    indicatorDiv.style.position = "fixed";
    indicatorDiv.style.width = "5px";
    indicatorDiv.style.height = "5px";
    indicatorDiv.style.backgroundColor = "grey";
    indicatorDiv.style.right = 0;
    indicatorDiv.style.top = 0;
    document.body.appendChild(indicatorDiv);

    console.log(`Browser Link JS has been loaded...`);
    const LS_BROSWER_ID_KEY = "__browser_link_browser_id";

    const getBrowserID = () => {
        const value = localStorage.getItem(LS_BROSWER_ID_KEY);
        if (value) {
            return value;
        }
        return undefined;
    };

    const setBrowserID = (value) => {
        localStorage.setItem(LS_BROSWER_ID_KEY, value);
    };

    let browser_id = getBrowserID();
    if (!browser_id) {
        const genRandomHex = size => [...Array(size)].map(() => Math.floor(Math.random() * 16).toString(16)).join('');
        const url = new URL(window.location.href);
        if (url.searchParams.has("external_auth") || url.searchParams.has("browser_link")) {
            browser_id = genRandomHex(16);
            setBrowserID(browser_id);
            console.log(`Browser ID created:`, browser_id);
        } else {
            console.info("Browser ID isn't set. Ingoring integration");
            return;    
        }
    }
    indicatorDiv.style.backgroundColor = "red";

    const debounce = (id, msec, cb) => {
        if (id) clearTimeout(id);
        return setTimeout(cb, msec);
    };
    
    let uriDebounce;

    const reportUriChange = (hass, uri) => {
        hass.conn.sendMessage({
            type: "browser_link/update_uri",
            browser_id,
            uri,
        });
    };
    
    const reportVisibility = (hass) => {
        hass.conn.sendMessage({
            type: "browser_link/update_visibility",
            browser_id,
            hidden: document.hidden,
        });
    };

    
    console.log(`Browser ID:`, browser_id);

    const onHassLoad = async (hass) => {

        console.log(`Hass loaded:`, hass);
        indicatorDiv.style.backgroundColor = "yellow";

        document.addEventListener("visibilitychange", () => {
            reportVisibility(hass);
        });

        let uri = window.location.pathname;

        window.addEventListener("location-changed", async (e) => {
            // console.log(`location-changed:`, e);
            uriDebounce = debounce(uriDebounce, 300, async () => {
                if (uri != window.location.pathname) {
                    uri = window.location.pathname;
                    console.log(`URI changed:`, uri);
                    reportUriChange(hass, uri);
                }
            });
        });
            
        const entities = await hass.conn.sendMessagePromise({
            type: "browser_link/get_entities",
            browser_id,
        });
        
        console.log(`Entites:`, entities);
        if (Object.keys(entities).length > 0) {
            indicatorDiv.style.backgroundColor = "lime";
        }

        const sendHAEvent = (name, detail) => {
            const evt = new CustomEvent(name, {
                bubbles: true,
                composed: true,
                cancelable: false,
                detail,
            });
            // console.log(`sendHAEvent`, name, detail, evt);
            document.querySelector("home-assistant").dispatchEvent(evt);
        }

        const reportMediaPlayerState = (hass, state, volume) => {
            hass.conn.sendMessage({
                type: "browser_link/media_player_state",
                browser_id,
                state,
                volume: Math.floor(volume * 100),
            });
        };
        
        const audioEl = new Audio();
        audioEl.addEventListener("ended", (e) => {
            console.log(`Play ended:`, e);
            reportMediaPlayerState(hass, "stop", 0);
        });
        audioEl.addEventListener("play", (e) => {
            console.log(`Play started:`, e);
            reportMediaPlayerState(hass, "play", audioEl.volume);
        });
        audioEl.addEventListener("pause", (e) => {
            console.log(`Play finished:`, e);
            reportMediaPlayerState(hass, "pause", audioEl.volume);
        });
        audioEl.addEventListener("volumechange", (e) => {
            console.log(`Play volume change:`, e);
            reportMediaPlayerState(hass, audioEl.ended? "stop": "play", audioEl.volume);
        });
        const playMedia = (url, volume) => {
            console.log(`playMedia:`, url, volume);

            if (!audioEl.ended) {
                audioEl.pause();
            }

            audioEl.src = url;
            if (volume >= 0) {
                audioEl.volume = volume / 100;
            }
            audioEl.play();
        };

        const emitHAAction = (type_, config) => {
            if (type_ == "more_info") {
                sendHAEvent("hass-more-info", {
                    entityId: config["entity_id"],
                });
            }
            if (type_ == "play_media") {
                playMedia(config["url"], config["volume"]);
            }
            if (type_ == "pause_media") {
                audioEl.pause();
            }
            if (type_ == "stop_media") {
                audioEl.pause();
                audioEl.src = "";
                reportMediaPlayerState(hass, "stop", 0);
            }
            if (type_ == "set_volume") {
                audioEl.volume = config["volume"] / 100;
            }
        };

        await hass.conn.subscribeEvents((e) => {
            if (entities[e.data.entity_id] == "uri") {
                const new_uri = e.data.new_state.state;
                // console.log(`Received URI update:`, e.data);
                if (new_uri != uri) {
                    console.log(`Changing URI:`, new_uri);
                    sendHAEvent("hass-action", {
                        action: "tap",
                        config: {
                            tap_action: {
                                action: "navigate",
                                navigation_path: new_uri,
                            }
                        }
                    });
                }
            }
            if (entities[e.data.entity_id] == "action") {
                console.log(`Action:`, e.data.new_state);
                emitHAAction(e.data.new_state.attributes.event_type, e.data.new_state.attributes);
            }
        }, "state_changed");
        reportUriChange(hass, uri);
        reportMediaPlayerState(hass, "stop", 0);
        reportVisibility(hass);
        // sendHAEvent("hass-notification", {
        //     message: `Browser Link: ${browser_id}`,
        //     duration: 5000,
        //     dismissable: true,
        // });
    };

    setTimeout(() => {
        hassConnection.then(onHassLoad);
    }, 0);
        
})();
