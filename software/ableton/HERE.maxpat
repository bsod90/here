{
  "patcher": {
    "fileversion": 1,
    "appversion": {
      "major": 8,
      "minor": 1,
      "revision": 2,
      "architecture": "x64",
      "modernui": 1
    },
    "classnamespace": "box",
    "rect": [
      60.0,
      100.0,
      1400.0,
      900.0
    ],
    "openrect": [
      0.0,
      0.0,
      600.0,
      168.0
    ],
    "bglocked": 0,
    "openinpresentation": 1,
    "default_fontsize": 10.0,
    "default_fontface": 0,
    "default_fontname": "Arial",
    "gridonopen": 1,
    "gridsize": [
      8.0,
      8.0
    ],
    "gridsnaponopen": 1,
    "objectsnaponopen": 1,
    "statusbarvisible": 2,
    "toolbarvisible": 1,
    "lefttoolbarpinned": 0,
    "toptoolbarpinned": 0,
    "righttoolbarpinned": 0,
    "bottomtoolbarpinned": 0,
    "toolbars_unpinned_last_save": 0,
    "tallnewobj": 0,
    "boxanimatetime": 500,
    "enablehscroll": 1,
    "enablevscroll": 1,
    "devicewidth": 600.0,
    "description": "HERE \u2014 MIDI \u2192 OSC controller for the HERE LED installation.",
    "digest": "HERE",
    "tags": "HERE OSC MIDI",
    "style": "",
    "subpatcher_template": "",
    "boxes": [
      {
        "box": {
          "id": "tab-1",
          "maxclass": "live.tab",
          "patching_rect": [
            1000.0,
            40.0,
            150.0,
            22.0
          ],
          "presentation": 1,
          "presentation_rect": [
            8.0,
            6.0,
            584.0,
            19.0
          ],
          "numinlets": 1,
          "numoutlets": 3,
          "outlettype": [
            "",
            "",
            "float"
          ],
          "parameter_enable": 1,
          "num_lines_patching": 6,
          "num_lines_presentation": 0,
          "varname": "here_view_tab",
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_enum": [
                "MIDI 1",
                "MIDI 2",
                "Master",
                "Rings",
                "Physics",
                "Conn"
              ],
              "parameter_initial": [
                0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_view",
              "parameter_shortname": "View",
              "parameter_mmax": 5,
              "parameter_type": 2,
              "parameter_unitstyle": 9
            }
          }
        }
      },
      {
        "box": {
          "id": "n-2",
          "maxclass": "newobj",
          "patching_rect": [
            20.0,
            40.0,
            60.0,
            22.0
          ],
          "text": "midiin"
        }
      },
      {
        "box": {
          "id": "n-3",
          "maxclass": "newobj",
          "patching_rect": [
            20.0,
            70.0,
            80.0,
            22.0
          ],
          "text": "midiparse"
        }
      },
      {
        "box": {
          "id": "n-4",
          "maxclass": "newobj",
          "patching_rect": [
            20.0,
            130.0,
            60.0,
            22.0
          ],
          "text": "midiout"
        }
      },
      {
        "box": {
          "id": "n-5",
          "maxclass": "newobj",
          "patching_rect": [
            120.0,
            100.0,
            100.0,
            22.0
          ],
          "text": "v8 here.js"
        }
      },
      {
        "box": {
          "id": "n-6",
          "maxclass": "newobj",
          "patching_rect": [
            20.0,
            100.0,
            60.0,
            22.0
          ],
          "text": "pack i i"
        }
      },
      {
        "box": {
          "id": "n-7",
          "maxclass": "newobj",
          "patching_rect": [
            20.0,
            130.0,
            80.0,
            22.0
          ],
          "text": "prepend note"
        }
      },
      {
        "box": {
          "id": "n-8",
          "maxclass": "newobj",
          "patching_rect": [
            760.0,
            540.0,
            200.0,
            22.0
          ],
          "text": "udpsend here.local 9000"
        }
      },
      {
        "box": {
          "id": "n-9",
          "maxclass": "newobj",
          "patching_rect": [
            240.0,
            160.0,
            110.0,
            22.0
          ],
          "text": "makenote 110 250"
        }
      },
      {
        "box": {
          "id": "n-10",
          "maxclass": "newobj",
          "patching_rect": [
            240.0,
            190.0,
            80.0,
            22.0
          ],
          "text": "midiformat"
        }
      },
      {
        "box": {
          "id": "t-11",
          "maxclass": "live.text",
          "patching_rect": [
            220.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "36 C1",
          "presentation": 1,
          "presentation_rect": [
            8.0,
            28.0,
            112.0,
            15.0
          ],
          "varname": "midi1__t_11",
          "texton": "36 C1",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_036",
              "parameter_shortname": "36",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-12",
          "maxclass": "live.comment",
          "patching_rect": [
            220.0,
            215.0,
            50.0,
            12.0
          ],
          "text": "Expand",
          "presentation": 1,
          "presentation_rect": [
            8.0,
            43.0,
            114.0,
            11.0
          ],
          "varname": "midi1__lc_12",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Expand"
        }
      },
      {
        "box": {
          "id": "n-13",
          "maxclass": "newobj",
          "patching_rect": [
            220.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-14",
          "maxclass": "message",
          "patching_rect": [
            220.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 36 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-15",
          "maxclass": "message",
          "patching_rect": [
            270.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 36",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-16",
          "maxclass": "message",
          "patching_rect": [
            220.0,
            290.0,
            40.0,
            18.0
          ],
          "text": "36",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-17",
          "maxclass": "live.text",
          "patching_rect": [
            246.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "37 C#1",
          "presentation": 1,
          "presentation_rect": [
            126.0,
            28.0,
            112.0,
            15.0
          ],
          "varname": "midi1__t_17",
          "texton": "37 C#1",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_037",
              "parameter_shortname": "37",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-18",
          "maxclass": "live.comment",
          "patching_rect": [
            246.0,
            215.0,
            50.0,
            12.0
          ],
          "text": "Contract",
          "presentation": 1,
          "presentation_rect": [
            126.0,
            43.0,
            114.0,
            11.0
          ],
          "varname": "midi1__lc_18",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Contract"
        }
      },
      {
        "box": {
          "id": "n-19",
          "maxclass": "newobj",
          "patching_rect": [
            246.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-20",
          "maxclass": "message",
          "patching_rect": [
            246.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 37 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-21",
          "maxclass": "message",
          "patching_rect": [
            296.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 37",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-22",
          "maxclass": "message",
          "patching_rect": [
            246.0,
            290.0,
            40.0,
            18.0
          ],
          "text": "37",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-23",
          "maxclass": "live.text",
          "patching_rect": [
            272.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "40 E1",
          "presentation": 1,
          "presentation_rect": [
            243.0,
            28.0,
            112.0,
            15.0
          ],
          "varname": "midi1__t_23",
          "texton": "40 E1",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_040",
              "parameter_shortname": "40",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-24",
          "maxclass": "live.comment",
          "patching_rect": [
            272.0,
            215.0,
            50.0,
            12.0
          ],
          "text": "Pulse",
          "presentation": 1,
          "presentation_rect": [
            243.0,
            43.0,
            114.0,
            11.0
          ],
          "varname": "midi1__lc_24",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Pulse"
        }
      },
      {
        "box": {
          "id": "n-25",
          "maxclass": "newobj",
          "patching_rect": [
            272.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-26",
          "maxclass": "message",
          "patching_rect": [
            272.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 40 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-27",
          "maxclass": "message",
          "patching_rect": [
            322.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 40",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-28",
          "maxclass": "message",
          "patching_rect": [
            272.0,
            290.0,
            40.0,
            18.0
          ],
          "text": "40",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-29",
          "maxclass": "live.text",
          "patching_rect": [
            298.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "41 F1",
          "presentation": 1,
          "presentation_rect": [
            361.0,
            28.0,
            112.0,
            15.0
          ],
          "varname": "midi1__t_29",
          "texton": "41 F1",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_041",
              "parameter_shortname": "41",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-30",
          "maxclass": "live.comment",
          "patching_rect": [
            298.0,
            215.0,
            50.0,
            12.0
          ],
          "text": "Blow Out",
          "presentation": 1,
          "presentation_rect": [
            361.0,
            43.0,
            114.0,
            11.0
          ],
          "varname": "midi1__lc_30",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Blow Out"
        }
      },
      {
        "box": {
          "id": "n-31",
          "maxclass": "newobj",
          "patching_rect": [
            298.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-32",
          "maxclass": "message",
          "patching_rect": [
            298.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 41 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-33",
          "maxclass": "message",
          "patching_rect": [
            348.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 41",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-34",
          "maxclass": "message",
          "patching_rect": [
            298.0,
            290.0,
            40.0,
            18.0
          ],
          "text": "41",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-35",
          "maxclass": "live.text",
          "patching_rect": [
            324.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "75 D#4",
          "presentation": 1,
          "presentation_rect": [
            478.0,
            28.0,
            112.0,
            15.0
          ],
          "varname": "midi1__t_35",
          "texton": "75 D#4",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_075",
              "parameter_shortname": "75",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-36",
          "maxclass": "live.comment",
          "patching_rect": [
            324.0,
            215.0,
            50.0,
            12.0
          ],
          "text": "Shimmer",
          "presentation": 1,
          "presentation_rect": [
            478.0,
            43.0,
            114.0,
            11.0
          ],
          "varname": "midi1__lc_36",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Shimmer"
        }
      },
      {
        "box": {
          "id": "n-37",
          "maxclass": "newobj",
          "patching_rect": [
            324.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-38",
          "maxclass": "message",
          "patching_rect": [
            324.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 75 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-39",
          "maxclass": "message",
          "patching_rect": [
            374.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 75",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-40",
          "maxclass": "message",
          "patching_rect": [
            324.0,
            290.0,
            40.0,
            18.0
          ],
          "text": "75",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-41",
          "maxclass": "live.text",
          "patching_rect": [
            350.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "42 F#1",
          "presentation": 1,
          "presentation_rect": [
            8.0,
            74.0,
            112.0,
            15.0
          ],
          "varname": "midi1__t_41",
          "texton": "42 F#1",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_042",
              "parameter_shortname": "42",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-42",
          "maxclass": "live.comment",
          "patching_rect": [
            350.0,
            215.0,
            50.0,
            12.0
          ],
          "text": "Regrow",
          "presentation": 1,
          "presentation_rect": [
            8.0,
            89.0,
            114.0,
            11.0
          ],
          "varname": "midi1__lc_42",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Regrow"
        }
      },
      {
        "box": {
          "id": "n-43",
          "maxclass": "newobj",
          "patching_rect": [
            350.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-44",
          "maxclass": "message",
          "patching_rect": [
            350.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 42 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-45",
          "maxclass": "message",
          "patching_rect": [
            400.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 42",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-46",
          "maxclass": "message",
          "patching_rect": [
            350.0,
            290.0,
            40.0,
            18.0
          ],
          "text": "42",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-47",
          "maxclass": "live.text",
          "patching_rect": [
            376.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "43 G1",
          "presentation": 1,
          "presentation_rect": [
            126.0,
            74.0,
            112.0,
            15.0
          ],
          "varname": "midi1__t_47",
          "texton": "43 G1",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_043",
              "parameter_shortname": "43",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-48",
          "maxclass": "live.comment",
          "patching_rect": [
            376.0,
            215.0,
            50.0,
            12.0
          ],
          "text": "Dissolve",
          "presentation": 1,
          "presentation_rect": [
            126.0,
            89.0,
            114.0,
            11.0
          ],
          "varname": "midi1__lc_48",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Dissolve"
        }
      },
      {
        "box": {
          "id": "n-49",
          "maxclass": "newobj",
          "patching_rect": [
            376.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-50",
          "maxclass": "message",
          "patching_rect": [
            376.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 43 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-51",
          "maxclass": "message",
          "patching_rect": [
            426.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 43",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-52",
          "maxclass": "message",
          "patching_rect": [
            376.0,
            290.0,
            40.0,
            18.0
          ],
          "text": "43",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-53",
          "maxclass": "live.text",
          "patching_rect": [
            402.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "44 G#1",
          "presentation": 1,
          "presentation_rect": [
            243.0,
            74.0,
            112.0,
            15.0
          ],
          "varname": "midi1__t_53",
          "texton": "44 G#1",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_044",
              "parameter_shortname": "44",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-54",
          "maxclass": "live.comment",
          "patching_rect": [
            402.0,
            215.0,
            50.0,
            12.0
          ],
          "text": "Respawn",
          "presentation": 1,
          "presentation_rect": [
            243.0,
            89.0,
            114.0,
            11.0
          ],
          "varname": "midi1__lc_54",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Respawn"
        }
      },
      {
        "box": {
          "id": "n-55",
          "maxclass": "newobj",
          "patching_rect": [
            402.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-56",
          "maxclass": "message",
          "patching_rect": [
            402.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 44 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-57",
          "maxclass": "message",
          "patching_rect": [
            452.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 44",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-58",
          "maxclass": "message",
          "patching_rect": [
            402.0,
            290.0,
            40.0,
            18.0
          ],
          "text": "44",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-59",
          "maxclass": "live.text",
          "patching_rect": [
            428.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "49 C#2",
          "presentation": 1,
          "presentation_rect": [
            361.0,
            74.0,
            112.0,
            15.0
          ],
          "varname": "midi1__t_59",
          "texton": "49 C#2",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_049",
              "parameter_shortname": "49",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-60",
          "maxclass": "live.comment",
          "patching_rect": [
            428.0,
            215.0,
            50.0,
            12.0
          ],
          "text": "Reset",
          "presentation": 1,
          "presentation_rect": [
            361.0,
            89.0,
            114.0,
            11.0
          ],
          "varname": "midi1__lc_60",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Reset"
        }
      },
      {
        "box": {
          "id": "n-61",
          "maxclass": "newobj",
          "patching_rect": [
            428.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-62",
          "maxclass": "message",
          "patching_rect": [
            428.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 49 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-63",
          "maxclass": "message",
          "patching_rect": [
            478.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 49",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-64",
          "maxclass": "message",
          "patching_rect": [
            428.0,
            290.0,
            40.0,
            18.0
          ],
          "text": "49",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-65",
          "maxclass": "live.text",
          "patching_rect": [
            454.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "50 D2",
          "presentation": 1,
          "presentation_rect": [
            478.0,
            74.0,
            112.0,
            15.0
          ],
          "varname": "midi1__t_65",
          "texton": "50 D2",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_050",
              "parameter_shortname": "50",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-66",
          "maxclass": "live.comment",
          "patching_rect": [
            454.0,
            215.0,
            50.0,
            12.0
          ],
          "text": "Fade Out",
          "presentation": 1,
          "presentation_rect": [
            478.0,
            89.0,
            114.0,
            11.0
          ],
          "varname": "midi1__lc_66",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Fade Out"
        }
      },
      {
        "box": {
          "id": "n-67",
          "maxclass": "newobj",
          "patching_rect": [
            454.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-68",
          "maxclass": "message",
          "patching_rect": [
            454.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 50 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-69",
          "maxclass": "message",
          "patching_rect": [
            504.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 50",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-70",
          "maxclass": "message",
          "patching_rect": [
            454.0,
            290.0,
            40.0,
            18.0
          ],
          "text": "50",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-71",
          "maxclass": "live.text",
          "patching_rect": [
            480.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "51 D#2",
          "presentation": 1,
          "presentation_rect": [
            8.0,
            120.0,
            78.0,
            15.0
          ],
          "varname": "midi1__t_71",
          "texton": "51 D#2",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_051",
              "parameter_shortname": "51",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-72",
          "maxclass": "live.comment",
          "patching_rect": [
            480.0,
            215.0,
            50.0,
            12.0
          ],
          "text": "Border",
          "presentation": 1,
          "presentation_rect": [
            8.0,
            135.0,
            80.0,
            11.0
          ],
          "varname": "midi1__lc_72",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Border"
        }
      },
      {
        "box": {
          "id": "n-73",
          "maxclass": "newobj",
          "patching_rect": [
            480.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-74",
          "maxclass": "message",
          "patching_rect": [
            480.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 51 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-75",
          "maxclass": "message",
          "patching_rect": [
            530.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 51",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-76",
          "maxclass": "message",
          "patching_rect": [
            480.0,
            290.0,
            40.0,
            18.0
          ],
          "text": "51",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-77",
          "maxclass": "live.text",
          "patching_rect": [
            506.0,
            200.0,
            24.0,
            14.0
          ],
          "text": "76 E4",
          "presentation": 1,
          "presentation_rect": [
            92.0,
            120.0,
            78.0,
            15.0
          ],
          "varname": "midi1__t_77",
          "texton": "76 E4",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_076",
              "parameter_shortname": "76",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-78",
          "maxclass": "live.comment",
          "patching_rect": [
            506.0,
            215.0,
            50.0,
            12.0
          ],
          "text": "Dissolve Border",
          "presentation": 1,
          "presentation_rect": [
            92.0,
            135.0,
            80.0,
            11.0
          ],
          "varname": "midi1__lc_78",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Dissolve Border"
        }
      },
      {
        "box": {
          "id": "n-79",
          "maxclass": "newobj",
          "patching_rect": [
            506.0,
            230.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-80",
          "maxclass": "message",
          "patching_rect": [
            506.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "note 76 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-81",
          "maxclass": "message",
          "patching_rect": [
            556.0,
            260.0,
            100.0,
            22.0
          ],
          "text": "noteoff 76",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-82",
          "maxclass": "message",
          "patching_rect": [
            506.0,
            290.0,
            40.0,
            18.0
          ],
          "text": "76",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-83",
          "maxclass": "live.text",
          "patching_rect": [
            220.0,
            320.0,
            24.0,
            14.0
          ],
          "text": "52 E2",
          "presentation": 1,
          "presentation_rect": [
            176.0,
            120.0,
            78.0,
            15.0
          ],
          "varname": "midi1__t_83",
          "texton": "52 E2",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_052",
              "parameter_shortname": "52",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-84",
          "maxclass": "live.comment",
          "patching_rect": [
            220.0,
            335.0,
            50.0,
            12.0
          ],
          "text": "Particles",
          "presentation": 1,
          "presentation_rect": [
            176.0,
            135.0,
            80.0,
            11.0
          ],
          "varname": "midi1__lc_84",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Particles"
        }
      },
      {
        "box": {
          "id": "n-85",
          "maxclass": "newobj",
          "patching_rect": [
            220.0,
            350.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-86",
          "maxclass": "message",
          "patching_rect": [
            220.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "note 52 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-87",
          "maxclass": "message",
          "patching_rect": [
            270.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "noteoff 52",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-88",
          "maxclass": "message",
          "patching_rect": [
            220.0,
            410.0,
            40.0,
            18.0
          ],
          "text": "52",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-89",
          "maxclass": "live.text",
          "patching_rect": [
            246.0,
            320.0,
            24.0,
            14.0
          ],
          "text": "45 A1",
          "presentation": 1,
          "presentation_rect": [
            260.0,
            120.0,
            78.0,
            15.0
          ],
          "varname": "midi1__t_89",
          "texton": "45 A1",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_045",
              "parameter_shortname": "45",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-90",
          "maxclass": "live.comment",
          "patching_rect": [
            246.0,
            335.0,
            50.0,
            12.0
          ],
          "text": "Palette 1",
          "presentation": 1,
          "presentation_rect": [
            260.0,
            135.0,
            80.0,
            11.0
          ],
          "varname": "midi1__lc_90",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Palette 1"
        }
      },
      {
        "box": {
          "id": "n-91",
          "maxclass": "newobj",
          "patching_rect": [
            246.0,
            350.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-92",
          "maxclass": "message",
          "patching_rect": [
            246.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "note 45 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-93",
          "maxclass": "message",
          "patching_rect": [
            296.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "noteoff 45",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-94",
          "maxclass": "message",
          "patching_rect": [
            246.0,
            410.0,
            40.0,
            18.0
          ],
          "text": "45",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-95",
          "maxclass": "live.text",
          "patching_rect": [
            272.0,
            320.0,
            24.0,
            14.0
          ],
          "text": "46 A#1",
          "presentation": 1,
          "presentation_rect": [
            344.0,
            120.0,
            78.0,
            15.0
          ],
          "varname": "midi1__t_95",
          "texton": "46 A#1",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_046",
              "parameter_shortname": "46",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-96",
          "maxclass": "live.comment",
          "patching_rect": [
            272.0,
            335.0,
            50.0,
            12.0
          ],
          "text": "Palette 2",
          "presentation": 1,
          "presentation_rect": [
            344.0,
            135.0,
            80.0,
            11.0
          ],
          "varname": "midi1__lc_96",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Palette 2"
        }
      },
      {
        "box": {
          "id": "n-97",
          "maxclass": "newobj",
          "patching_rect": [
            272.0,
            350.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-98",
          "maxclass": "message",
          "patching_rect": [
            272.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "note 46 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-99",
          "maxclass": "message",
          "patching_rect": [
            322.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "noteoff 46",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-100",
          "maxclass": "message",
          "patching_rect": [
            272.0,
            410.0,
            40.0,
            18.0
          ],
          "text": "46",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-101",
          "maxclass": "live.text",
          "patching_rect": [
            298.0,
            320.0,
            24.0,
            14.0
          ],
          "text": "47 B1",
          "presentation": 1,
          "presentation_rect": [
            428.0,
            120.0,
            78.0,
            15.0
          ],
          "varname": "midi1__t_101",
          "texton": "47 B1",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_047",
              "parameter_shortname": "47",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-102",
          "maxclass": "live.comment",
          "patching_rect": [
            298.0,
            335.0,
            50.0,
            12.0
          ],
          "text": "Palette 3",
          "presentation": 1,
          "presentation_rect": [
            428.0,
            135.0,
            80.0,
            11.0
          ],
          "varname": "midi1__lc_102",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Palette 3"
        }
      },
      {
        "box": {
          "id": "n-103",
          "maxclass": "newobj",
          "patching_rect": [
            298.0,
            350.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-104",
          "maxclass": "message",
          "patching_rect": [
            298.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "note 47 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-105",
          "maxclass": "message",
          "patching_rect": [
            348.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "noteoff 47",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-106",
          "maxclass": "message",
          "patching_rect": [
            298.0,
            410.0,
            40.0,
            18.0
          ],
          "text": "47",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-107",
          "maxclass": "live.text",
          "patching_rect": [
            324.0,
            320.0,
            24.0,
            14.0
          ],
          "text": "48 C2",
          "presentation": 1,
          "presentation_rect": [
            512.0,
            120.0,
            78.0,
            15.0
          ],
          "varname": "midi1__t_107",
          "texton": "48 C2",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_048",
              "parameter_shortname": "48",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-108",
          "maxclass": "live.comment",
          "patching_rect": [
            324.0,
            335.0,
            50.0,
            12.0
          ],
          "text": "Palette 4",
          "presentation": 1,
          "presentation_rect": [
            512.0,
            135.0,
            80.0,
            11.0
          ],
          "varname": "midi1__lc_108",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Palette 4"
        }
      },
      {
        "box": {
          "id": "n-109",
          "maxclass": "newobj",
          "patching_rect": [
            324.0,
            350.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-110",
          "maxclass": "message",
          "patching_rect": [
            324.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "note 48 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-111",
          "maxclass": "message",
          "patching_rect": [
            374.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "noteoff 48",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-112",
          "maxclass": "message",
          "patching_rect": [
            324.0,
            410.0,
            40.0,
            18.0
          ],
          "text": "48",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-113",
          "maxclass": "live.text",
          "patching_rect": [
            350.0,
            320.0,
            24.0,
            14.0
          ],
          "text": "38 D1",
          "presentation": 1,
          "presentation_rect": [
            8.0,
            28.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_113",
          "texton": "38 D1",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_038",
              "parameter_shortname": "38",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-114",
          "maxclass": "live.comment",
          "patching_rect": [
            350.0,
            335.0,
            50.0,
            12.0
          ],
          "text": "Rotate CW",
          "presentation": 1,
          "presentation_rect": [
            8.0,
            43.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_114",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Rotate CW"
        }
      },
      {
        "box": {
          "id": "n-115",
          "maxclass": "newobj",
          "patching_rect": [
            350.0,
            350.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-116",
          "maxclass": "message",
          "patching_rect": [
            350.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "note 38 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-117",
          "maxclass": "message",
          "patching_rect": [
            400.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "noteoff 38",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-118",
          "maxclass": "message",
          "patching_rect": [
            350.0,
            410.0,
            40.0,
            18.0
          ],
          "text": "38",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-119",
          "maxclass": "live.text",
          "patching_rect": [
            376.0,
            320.0,
            24.0,
            14.0
          ],
          "text": "39 D#1",
          "presentation": 1,
          "presentation_rect": [
            82.0,
            28.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_119",
          "texton": "39 D#1",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_039",
              "parameter_shortname": "39",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-120",
          "maxclass": "live.comment",
          "patching_rect": [
            376.0,
            335.0,
            50.0,
            12.0
          ],
          "text": "Rotate CCW",
          "presentation": 1,
          "presentation_rect": [
            82.0,
            43.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_120",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Rotate CCW"
        }
      },
      {
        "box": {
          "id": "n-121",
          "maxclass": "newobj",
          "patching_rect": [
            376.0,
            350.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-122",
          "maxclass": "message",
          "patching_rect": [
            376.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "note 39 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-123",
          "maxclass": "message",
          "patching_rect": [
            426.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "noteoff 39",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-124",
          "maxclass": "message",
          "patching_rect": [
            376.0,
            410.0,
            40.0,
            18.0
          ],
          "text": "39",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-125",
          "maxclass": "live.text",
          "patching_rect": [
            402.0,
            320.0,
            24.0,
            14.0
          ],
          "text": "54 F#2",
          "presentation": 1,
          "presentation_rect": [
            155.0,
            28.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_125",
          "texton": "54 F#2",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_054",
              "parameter_shortname": "54",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-126",
          "maxclass": "live.comment",
          "patching_rect": [
            402.0,
            335.0,
            50.0,
            12.0
          ],
          "text": "Outer CW",
          "presentation": 1,
          "presentation_rect": [
            155.0,
            43.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_126",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Outer CW"
        }
      },
      {
        "box": {
          "id": "n-127",
          "maxclass": "newobj",
          "patching_rect": [
            402.0,
            350.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-128",
          "maxclass": "message",
          "patching_rect": [
            402.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "note 54 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-129",
          "maxclass": "message",
          "patching_rect": [
            452.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "noteoff 54",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-130",
          "maxclass": "message",
          "patching_rect": [
            402.0,
            410.0,
            40.0,
            18.0
          ],
          "text": "54",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-131",
          "maxclass": "live.text",
          "patching_rect": [
            428.0,
            320.0,
            24.0,
            14.0
          ],
          "text": "55 G2",
          "presentation": 1,
          "presentation_rect": [
            228.0,
            28.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_131",
          "texton": "55 G2",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_055",
              "parameter_shortname": "55",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-132",
          "maxclass": "live.comment",
          "patching_rect": [
            428.0,
            335.0,
            50.0,
            12.0
          ],
          "text": "Outer CCW",
          "presentation": 1,
          "presentation_rect": [
            228.0,
            43.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_132",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Outer CCW"
        }
      },
      {
        "box": {
          "id": "n-133",
          "maxclass": "newobj",
          "patching_rect": [
            428.0,
            350.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-134",
          "maxclass": "message",
          "patching_rect": [
            428.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "note 55 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-135",
          "maxclass": "message",
          "patching_rect": [
            478.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "noteoff 55",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-136",
          "maxclass": "message",
          "patching_rect": [
            428.0,
            410.0,
            40.0,
            18.0
          ],
          "text": "55",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-137",
          "maxclass": "live.text",
          "patching_rect": [
            454.0,
            320.0,
            24.0,
            14.0
          ],
          "text": "56 G#2",
          "presentation": 1,
          "presentation_rect": [
            302.0,
            28.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_137",
          "texton": "56 G#2",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_056",
              "parameter_shortname": "56",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-138",
          "maxclass": "live.comment",
          "patching_rect": [
            454.0,
            335.0,
            50.0,
            12.0
          ],
          "text": "Middle CW",
          "presentation": 1,
          "presentation_rect": [
            302.0,
            43.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_138",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Middle CW"
        }
      },
      {
        "box": {
          "id": "n-139",
          "maxclass": "newobj",
          "patching_rect": [
            454.0,
            350.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-140",
          "maxclass": "message",
          "patching_rect": [
            454.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "note 56 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-141",
          "maxclass": "message",
          "patching_rect": [
            504.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "noteoff 56",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-142",
          "maxclass": "message",
          "patching_rect": [
            454.0,
            410.0,
            40.0,
            18.0
          ],
          "text": "56",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-143",
          "maxclass": "live.text",
          "patching_rect": [
            480.0,
            320.0,
            24.0,
            14.0
          ],
          "text": "57 A2",
          "presentation": 1,
          "presentation_rect": [
            376.0,
            28.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_143",
          "texton": "57 A2",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_057",
              "parameter_shortname": "57",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-144",
          "maxclass": "live.comment",
          "patching_rect": [
            480.0,
            335.0,
            50.0,
            12.0
          ],
          "text": "Middle CCW",
          "presentation": 1,
          "presentation_rect": [
            376.0,
            43.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_144",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Middle CCW"
        }
      },
      {
        "box": {
          "id": "n-145",
          "maxclass": "newobj",
          "patching_rect": [
            480.0,
            350.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-146",
          "maxclass": "message",
          "patching_rect": [
            480.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "note 57 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-147",
          "maxclass": "message",
          "patching_rect": [
            530.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "noteoff 57",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-148",
          "maxclass": "message",
          "patching_rect": [
            480.0,
            410.0,
            40.0,
            18.0
          ],
          "text": "57",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-149",
          "maxclass": "live.text",
          "patching_rect": [
            506.0,
            320.0,
            24.0,
            14.0
          ],
          "text": "58 A#2",
          "presentation": 1,
          "presentation_rect": [
            449.0,
            28.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_149",
          "texton": "58 A#2",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_058",
              "parameter_shortname": "58",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-150",
          "maxclass": "live.comment",
          "patching_rect": [
            506.0,
            335.0,
            50.0,
            12.0
          ],
          "text": "Inner CW",
          "presentation": 1,
          "presentation_rect": [
            449.0,
            43.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_150",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Inner CW"
        }
      },
      {
        "box": {
          "id": "n-151",
          "maxclass": "newobj",
          "patching_rect": [
            506.0,
            350.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-152",
          "maxclass": "message",
          "patching_rect": [
            506.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "note 58 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-153",
          "maxclass": "message",
          "patching_rect": [
            556.0,
            380.0,
            100.0,
            22.0
          ],
          "text": "noteoff 58",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-154",
          "maxclass": "message",
          "patching_rect": [
            506.0,
            410.0,
            40.0,
            18.0
          ],
          "text": "58",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-155",
          "maxclass": "live.text",
          "patching_rect": [
            220.0,
            440.0,
            24.0,
            14.0
          ],
          "text": "59 B2",
          "presentation": 1,
          "presentation_rect": [
            522.0,
            28.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_155",
          "texton": "59 B2",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_059",
              "parameter_shortname": "59",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-156",
          "maxclass": "live.comment",
          "patching_rect": [
            220.0,
            455.0,
            50.0,
            12.0
          ],
          "text": "Inner CCW",
          "presentation": 1,
          "presentation_rect": [
            522.0,
            43.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_156",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Inner CCW"
        }
      },
      {
        "box": {
          "id": "n-157",
          "maxclass": "newobj",
          "patching_rect": [
            220.0,
            470.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-158",
          "maxclass": "message",
          "patching_rect": [
            220.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "note 59 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-159",
          "maxclass": "message",
          "patching_rect": [
            270.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "noteoff 59",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-160",
          "maxclass": "message",
          "patching_rect": [
            220.0,
            530.0,
            40.0,
            18.0
          ],
          "text": "59",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-161",
          "maxclass": "live.text",
          "patching_rect": [
            246.0,
            440.0,
            24.0,
            14.0
          ],
          "text": "60 C3",
          "presentation": 1,
          "presentation_rect": [
            8.0,
            74.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_161",
          "texton": "60 C3",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_060",
              "parameter_shortname": "60",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-162",
          "maxclass": "live.comment",
          "patching_rect": [
            246.0,
            455.0,
            50.0,
            12.0
          ],
          "text": "Stop Rot All",
          "presentation": 1,
          "presentation_rect": [
            8.0,
            89.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_162",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Stop Rot All"
        }
      },
      {
        "box": {
          "id": "n-163",
          "maxclass": "newobj",
          "patching_rect": [
            246.0,
            470.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-164",
          "maxclass": "message",
          "patching_rect": [
            246.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "note 60 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-165",
          "maxclass": "message",
          "patching_rect": [
            296.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "noteoff 60",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-166",
          "maxclass": "message",
          "patching_rect": [
            246.0,
            530.0,
            40.0,
            18.0
          ],
          "text": "60",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-167",
          "maxclass": "live.text",
          "patching_rect": [
            272.0,
            440.0,
            24.0,
            14.0
          ],
          "text": "61 C#3",
          "presentation": 1,
          "presentation_rect": [
            82.0,
            74.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_167",
          "texton": "61 C#3",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_061",
              "parameter_shortname": "61",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-168",
          "maxclass": "live.comment",
          "patching_rect": [
            272.0,
            455.0,
            50.0,
            12.0
          ],
          "text": "Stop Outer",
          "presentation": 1,
          "presentation_rect": [
            82.0,
            89.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_168",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Stop Outer"
        }
      },
      {
        "box": {
          "id": "n-169",
          "maxclass": "newobj",
          "patching_rect": [
            272.0,
            470.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-170",
          "maxclass": "message",
          "patching_rect": [
            272.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "note 61 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-171",
          "maxclass": "message",
          "patching_rect": [
            322.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "noteoff 61",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-172",
          "maxclass": "message",
          "patching_rect": [
            272.0,
            530.0,
            40.0,
            18.0
          ],
          "text": "61",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-173",
          "maxclass": "live.text",
          "patching_rect": [
            298.0,
            440.0,
            24.0,
            14.0
          ],
          "text": "62 D3",
          "presentation": 1,
          "presentation_rect": [
            155.0,
            74.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_173",
          "texton": "62 D3",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_062",
              "parameter_shortname": "62",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-174",
          "maxclass": "live.comment",
          "patching_rect": [
            298.0,
            455.0,
            50.0,
            12.0
          ],
          "text": "Stop Middle",
          "presentation": 1,
          "presentation_rect": [
            155.0,
            89.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_174",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Stop Middle"
        }
      },
      {
        "box": {
          "id": "n-175",
          "maxclass": "newobj",
          "patching_rect": [
            298.0,
            470.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-176",
          "maxclass": "message",
          "patching_rect": [
            298.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "note 62 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-177",
          "maxclass": "message",
          "patching_rect": [
            348.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "noteoff 62",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-178",
          "maxclass": "message",
          "patching_rect": [
            298.0,
            530.0,
            40.0,
            18.0
          ],
          "text": "62",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-179",
          "maxclass": "live.text",
          "patching_rect": [
            324.0,
            440.0,
            24.0,
            14.0
          ],
          "text": "63 D#3",
          "presentation": 1,
          "presentation_rect": [
            228.0,
            74.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_179",
          "texton": "63 D#3",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_063",
              "parameter_shortname": "63",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-180",
          "maxclass": "live.comment",
          "patching_rect": [
            324.0,
            455.0,
            50.0,
            12.0
          ],
          "text": "Stop Inner",
          "presentation": 1,
          "presentation_rect": [
            228.0,
            89.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_180",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Stop Inner"
        }
      },
      {
        "box": {
          "id": "n-181",
          "maxclass": "newobj",
          "patching_rect": [
            324.0,
            470.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-182",
          "maxclass": "message",
          "patching_rect": [
            324.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "note 63 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-183",
          "maxclass": "message",
          "patching_rect": [
            374.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "noteoff 63",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-184",
          "maxclass": "message",
          "patching_rect": [
            324.0,
            530.0,
            40.0,
            18.0
          ],
          "text": "63",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-185",
          "maxclass": "live.text",
          "patching_rect": [
            350.0,
            440.0,
            24.0,
            14.0
          ],
          "text": "65 F3",
          "presentation": 1,
          "presentation_rect": [
            302.0,
            74.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_185",
          "texton": "65 F3",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_065",
              "parameter_shortname": "65",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-186",
          "maxclass": "live.comment",
          "patching_rect": [
            350.0,
            455.0,
            50.0,
            12.0
          ],
          "text": "Show Outer",
          "presentation": 1,
          "presentation_rect": [
            302.0,
            89.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_186",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Show Outer"
        }
      },
      {
        "box": {
          "id": "n-187",
          "maxclass": "newobj",
          "patching_rect": [
            350.0,
            470.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-188",
          "maxclass": "message",
          "patching_rect": [
            350.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "note 65 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-189",
          "maxclass": "message",
          "patching_rect": [
            400.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "noteoff 65",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-190",
          "maxclass": "message",
          "patching_rect": [
            350.0,
            530.0,
            40.0,
            18.0
          ],
          "text": "65",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-191",
          "maxclass": "live.text",
          "patching_rect": [
            376.0,
            440.0,
            24.0,
            14.0
          ],
          "text": "66 F#3",
          "presentation": 1,
          "presentation_rect": [
            376.0,
            74.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_191",
          "texton": "66 F#3",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_066",
              "parameter_shortname": "66",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-192",
          "maxclass": "live.comment",
          "patching_rect": [
            376.0,
            455.0,
            50.0,
            12.0
          ],
          "text": "Hide Outer",
          "presentation": 1,
          "presentation_rect": [
            376.0,
            89.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_192",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Hide Outer"
        }
      },
      {
        "box": {
          "id": "n-193",
          "maxclass": "newobj",
          "patching_rect": [
            376.0,
            470.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-194",
          "maxclass": "message",
          "patching_rect": [
            376.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "note 66 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-195",
          "maxclass": "message",
          "patching_rect": [
            426.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "noteoff 66",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-196",
          "maxclass": "message",
          "patching_rect": [
            376.0,
            530.0,
            40.0,
            18.0
          ],
          "text": "66",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-197",
          "maxclass": "live.text",
          "patching_rect": [
            402.0,
            440.0,
            24.0,
            14.0
          ],
          "text": "67 G3",
          "presentation": 1,
          "presentation_rect": [
            449.0,
            74.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_197",
          "texton": "67 G3",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_067",
              "parameter_shortname": "67",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-198",
          "maxclass": "live.comment",
          "patching_rect": [
            402.0,
            455.0,
            50.0,
            12.0
          ],
          "text": "Show Middle",
          "presentation": 1,
          "presentation_rect": [
            449.0,
            89.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_198",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Show Middle"
        }
      },
      {
        "box": {
          "id": "n-199",
          "maxclass": "newobj",
          "patching_rect": [
            402.0,
            470.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-200",
          "maxclass": "message",
          "patching_rect": [
            402.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "note 67 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-201",
          "maxclass": "message",
          "patching_rect": [
            452.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "noteoff 67",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-202",
          "maxclass": "message",
          "patching_rect": [
            402.0,
            530.0,
            40.0,
            18.0
          ],
          "text": "67",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-203",
          "maxclass": "live.text",
          "patching_rect": [
            428.0,
            440.0,
            24.0,
            14.0
          ],
          "text": "68 G#3",
          "presentation": 1,
          "presentation_rect": [
            522.0,
            74.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_203",
          "texton": "68 G#3",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_068",
              "parameter_shortname": "68",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-204",
          "maxclass": "live.comment",
          "patching_rect": [
            428.0,
            455.0,
            50.0,
            12.0
          ],
          "text": "Hide Middle",
          "presentation": 1,
          "presentation_rect": [
            522.0,
            89.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_204",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Hide Middle"
        }
      },
      {
        "box": {
          "id": "n-205",
          "maxclass": "newobj",
          "patching_rect": [
            428.0,
            470.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-206",
          "maxclass": "message",
          "patching_rect": [
            428.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "note 68 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-207",
          "maxclass": "message",
          "patching_rect": [
            478.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "noteoff 68",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-208",
          "maxclass": "message",
          "patching_rect": [
            428.0,
            530.0,
            40.0,
            18.0
          ],
          "text": "68",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-209",
          "maxclass": "live.text",
          "patching_rect": [
            454.0,
            440.0,
            24.0,
            14.0
          ],
          "text": "69 A3",
          "presentation": 1,
          "presentation_rect": [
            8.0,
            120.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_209",
          "texton": "69 A3",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_069",
              "parameter_shortname": "69",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-210",
          "maxclass": "live.comment",
          "patching_rect": [
            454.0,
            455.0,
            50.0,
            12.0
          ],
          "text": "Show Inner",
          "presentation": 1,
          "presentation_rect": [
            8.0,
            135.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_210",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Show Inner"
        }
      },
      {
        "box": {
          "id": "n-211",
          "maxclass": "newobj",
          "patching_rect": [
            454.0,
            470.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-212",
          "maxclass": "message",
          "patching_rect": [
            454.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "note 69 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-213",
          "maxclass": "message",
          "patching_rect": [
            504.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "noteoff 69",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-214",
          "maxclass": "message",
          "patching_rect": [
            454.0,
            530.0,
            40.0,
            18.0
          ],
          "text": "69",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-215",
          "maxclass": "live.text",
          "patching_rect": [
            480.0,
            440.0,
            24.0,
            14.0
          ],
          "text": "70 A#3",
          "presentation": 1,
          "presentation_rect": [
            82.0,
            120.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_215",
          "texton": "70 A#3",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_070",
              "parameter_shortname": "70",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-216",
          "maxclass": "live.comment",
          "patching_rect": [
            480.0,
            455.0,
            50.0,
            12.0
          ],
          "text": "Hide Inner",
          "presentation": 1,
          "presentation_rect": [
            82.0,
            135.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_216",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Hide Inner"
        }
      },
      {
        "box": {
          "id": "n-217",
          "maxclass": "newobj",
          "patching_rect": [
            480.0,
            470.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-218",
          "maxclass": "message",
          "patching_rect": [
            480.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "note 70 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-219",
          "maxclass": "message",
          "patching_rect": [
            530.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "noteoff 70",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-220",
          "maxclass": "message",
          "patching_rect": [
            480.0,
            530.0,
            40.0,
            18.0
          ],
          "text": "70",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-221",
          "maxclass": "live.text",
          "patching_rect": [
            506.0,
            440.0,
            24.0,
            14.0
          ],
          "text": "71 B3",
          "presentation": 1,
          "presentation_rect": [
            155.0,
            120.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_221",
          "texton": "71 B3",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_071",
              "parameter_shortname": "71",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-222",
          "maxclass": "live.comment",
          "patching_rect": [
            506.0,
            455.0,
            50.0,
            12.0
          ],
          "text": "Meteors",
          "presentation": 1,
          "presentation_rect": [
            155.0,
            135.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_222",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Meteors"
        }
      },
      {
        "box": {
          "id": "n-223",
          "maxclass": "newobj",
          "patching_rect": [
            506.0,
            470.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-224",
          "maxclass": "message",
          "patching_rect": [
            506.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "note 71 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-225",
          "maxclass": "message",
          "patching_rect": [
            556.0,
            500.0,
            100.0,
            22.0
          ],
          "text": "noteoff 71",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-226",
          "maxclass": "message",
          "patching_rect": [
            506.0,
            530.0,
            40.0,
            18.0
          ],
          "text": "71",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-227",
          "maxclass": "live.text",
          "patching_rect": [
            220.0,
            560.0,
            24.0,
            14.0
          ],
          "text": "72 C4",
          "presentation": 1,
          "presentation_rect": [
            228.0,
            120.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_227",
          "texton": "72 C4",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_072",
              "parameter_shortname": "72",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-228",
          "maxclass": "live.comment",
          "patching_rect": [
            220.0,
            575.0,
            50.0,
            12.0
          ],
          "text": "Dust",
          "presentation": 1,
          "presentation_rect": [
            228.0,
            135.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_228",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Dust"
        }
      },
      {
        "box": {
          "id": "n-229",
          "maxclass": "newobj",
          "patching_rect": [
            220.0,
            590.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-230",
          "maxclass": "message",
          "patching_rect": [
            220.0,
            620.0,
            100.0,
            22.0
          ],
          "text": "note 72 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-231",
          "maxclass": "message",
          "patching_rect": [
            270.0,
            620.0,
            100.0,
            22.0
          ],
          "text": "noteoff 72",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-232",
          "maxclass": "message",
          "patching_rect": [
            220.0,
            650.0,
            40.0,
            18.0
          ],
          "text": "72",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-233",
          "maxclass": "live.text",
          "patching_rect": [
            246.0,
            560.0,
            24.0,
            14.0
          ],
          "text": "73 C#4",
          "presentation": 1,
          "presentation_rect": [
            302.0,
            120.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_233",
          "texton": "73 C#4",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_073",
              "parameter_shortname": "73",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-234",
          "maxclass": "live.comment",
          "patching_rect": [
            246.0,
            575.0,
            50.0,
            12.0
          ],
          "text": "Flash",
          "presentation": 1,
          "presentation_rect": [
            302.0,
            135.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_234",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Flash"
        }
      },
      {
        "box": {
          "id": "n-235",
          "maxclass": "newobj",
          "patching_rect": [
            246.0,
            590.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-236",
          "maxclass": "message",
          "patching_rect": [
            246.0,
            620.0,
            100.0,
            22.0
          ],
          "text": "note 73 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-237",
          "maxclass": "message",
          "patching_rect": [
            296.0,
            620.0,
            100.0,
            22.0
          ],
          "text": "noteoff 73",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-238",
          "maxclass": "message",
          "patching_rect": [
            246.0,
            650.0,
            40.0,
            18.0
          ],
          "text": "73",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-239",
          "maxclass": "live.text",
          "patching_rect": [
            272.0,
            560.0,
            24.0,
            14.0
          ],
          "text": "74 D4",
          "presentation": 1,
          "presentation_rect": [
            376.0,
            120.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_239",
          "texton": "74 D4",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_074",
              "parameter_shortname": "74",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-240",
          "maxclass": "live.comment",
          "patching_rect": [
            272.0,
            575.0,
            50.0,
            12.0
          ],
          "text": "Wipe",
          "presentation": 1,
          "presentation_rect": [
            376.0,
            135.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_240",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Wipe"
        }
      },
      {
        "box": {
          "id": "n-241",
          "maxclass": "newobj",
          "patching_rect": [
            272.0,
            590.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-242",
          "maxclass": "message",
          "patching_rect": [
            272.0,
            620.0,
            100.0,
            22.0
          ],
          "text": "note 74 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-243",
          "maxclass": "message",
          "patching_rect": [
            322.0,
            620.0,
            100.0,
            22.0
          ],
          "text": "noteoff 74",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-244",
          "maxclass": "message",
          "patching_rect": [
            272.0,
            650.0,
            40.0,
            18.0
          ],
          "text": "74",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-245",
          "maxclass": "live.text",
          "patching_rect": [
            298.0,
            560.0,
            24.0,
            14.0
          ],
          "text": "53 F2",
          "presentation": 1,
          "presentation_rect": [
            449.0,
            120.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_245",
          "texton": "53 F2",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_053",
              "parameter_shortname": "53",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-246",
          "maxclass": "live.comment",
          "patching_rect": [
            298.0,
            575.0,
            50.0,
            12.0
          ],
          "text": "Pull Center",
          "presentation": 1,
          "presentation_rect": [
            449.0,
            135.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_246",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Pull Center"
        }
      },
      {
        "box": {
          "id": "n-247",
          "maxclass": "newobj",
          "patching_rect": [
            298.0,
            590.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-248",
          "maxclass": "message",
          "patching_rect": [
            298.0,
            620.0,
            100.0,
            22.0
          ],
          "text": "note 53 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-249",
          "maxclass": "message",
          "patching_rect": [
            348.0,
            620.0,
            100.0,
            22.0
          ],
          "text": "noteoff 53",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-250",
          "maxclass": "message",
          "patching_rect": [
            298.0,
            650.0,
            40.0,
            18.0
          ],
          "text": "53",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "t-251",
          "maxclass": "live.text",
          "patching_rect": [
            324.0,
            560.0,
            24.0,
            14.0
          ],
          "text": "64 E3",
          "presentation": 1,
          "presentation_rect": [
            522.0,
            120.0,
            68.0,
            15.0
          ],
          "varname": "midi2__t_251",
          "texton": "64 E3",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "mode": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "pad_064",
              "parameter_shortname": "64",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-252",
          "maxclass": "live.comment",
          "patching_rect": [
            324.0,
            575.0,
            50.0,
            12.0
          ],
          "text": "Push Random",
          "presentation": 1,
          "presentation_rect": [
            522.0,
            135.0,
            70.0,
            11.0
          ],
          "varname": "midi2__lc_252",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Push Random"
        }
      },
      {
        "box": {
          "id": "n-253",
          "maxclass": "newobj",
          "patching_rect": [
            324.0,
            590.0,
            60.0,
            22.0
          ],
          "text": "route 1 0"
        }
      },
      {
        "box": {
          "id": "m-254",
          "maxclass": "message",
          "patching_rect": [
            324.0,
            620.0,
            100.0,
            22.0
          ],
          "text": "note 64 1",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-255",
          "maxclass": "message",
          "patching_rect": [
            374.0,
            620.0,
            100.0,
            22.0
          ],
          "text": "noteoff 64",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-256",
          "maxclass": "message",
          "patching_rect": [
            324.0,
            650.0,
            40.0,
            18.0
          ],
          "text": "64",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "d-257",
          "maxclass": "live.dial",
          "patching_rect": [
            420.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            13.0,
            40.0,
            42.0,
            42.0
          ],
          "varname": "master__d_257",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                2.5
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_radius_min",
              "parameter_shortname": "Radius Min",
              "parameter_mmax": 12.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-258",
          "maxclass": "live.comment",
          "patching_rect": [
            420.0,
            686.0,
            60.0,
            12.0
          ],
          "text": "Radius Min",
          "presentation": 1,
          "presentation_rect": [
            8.0,
            84.0,
            52.0,
            12.0
          ],
          "varname": "master__lc_258",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Radius Min"
        }
      },
      {
        "box": {
          "id": "n-259",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            740.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-260",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            766.0,
            200.0,
            22.0
          ],
          "text": "prepend knob master radius_min"
        }
      },
      {
        "box": {
          "id": "d-261",
          "maxclass": "live.dial",
          "patching_rect": [
            456.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            65.0,
            40.0,
            42.0,
            42.0
          ],
          "varname": "master__d_261",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                16.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_radius_max",
              "parameter_shortname": "Radius Max",
              "parameter_mmax": 22.0,
              "parameter_mmin": 8.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-262",
          "maxclass": "live.comment",
          "patching_rect": [
            456.0,
            686.0,
            60.0,
            12.0
          ],
          "text": "Radius Max",
          "presentation": 1,
          "presentation_rect": [
            60.0,
            84.0,
            52.0,
            12.0
          ],
          "varname": "master__lc_262",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Radius Max"
        }
      },
      {
        "box": {
          "id": "n-263",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            740.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-264",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            766.0,
            200.0,
            22.0
          ],
          "text": "prepend knob master radius_max"
        }
      },
      {
        "box": {
          "id": "d-265",
          "maxclass": "live.dial",
          "patching_rect": [
            492.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            117.0,
            40.0,
            42.0,
            42.0
          ],
          "varname": "master__d_265",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                8.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_radius_default",
              "parameter_shortname": "Radius Defa",
              "parameter_mmax": 20.0,
              "parameter_mmin": 2.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-266",
          "maxclass": "live.comment",
          "patching_rect": [
            492.0,
            686.0,
            60.0,
            12.0
          ],
          "text": "Radius Default",
          "presentation": 1,
          "presentation_rect": [
            112.0,
            84.0,
            52.0,
            12.0
          ],
          "varname": "master__lc_266",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Radius Default"
        }
      },
      {
        "box": {
          "id": "n-267",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            740.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-268",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            766.0,
            200.0,
            22.0
          ],
          "text": "prepend knob master radius_default"
        }
      },
      {
        "box": {
          "id": "d-269",
          "maxclass": "live.dial",
          "patching_rect": [
            528.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            169.0,
            40.0,
            42.0,
            42.0
          ],
          "varname": "master__d_269",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_brightness",
              "parameter_shortname": "Brightness",
              "parameter_mmax": 2.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-270",
          "maxclass": "live.comment",
          "patching_rect": [
            528.0,
            686.0,
            60.0,
            12.0
          ],
          "text": "Brightness",
          "presentation": 1,
          "presentation_rect": [
            164.0,
            84.0,
            52.0,
            12.0
          ],
          "varname": "master__lc_270",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Brightness"
        }
      },
      {
        "box": {
          "id": "n-271",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            740.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-272",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            766.0,
            200.0,
            22.0
          ],
          "text": "prepend knob master brightness"
        }
      },
      {
        "box": {
          "id": "d-273",
          "maxclass": "live.dial",
          "patching_rect": [
            564.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            221.0,
            40.0,
            42.0,
            42.0
          ],
          "varname": "master__d_273",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_gap_coefficient",
              "parameter_shortname": "Ring Gap",
              "parameter_mmax": 6.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-274",
          "maxclass": "live.comment",
          "patching_rect": [
            564.0,
            686.0,
            60.0,
            12.0
          ],
          "text": "Ring Gap",
          "presentation": 1,
          "presentation_rect": [
            216.0,
            84.0,
            52.0,
            12.0
          ],
          "varname": "master__lc_274",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Ring Gap"
        }
      },
      {
        "box": {
          "id": "n-275",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            740.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-276",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            766.0,
            200.0,
            22.0
          ],
          "text": "prepend knob master gap_coefficient"
        }
      },
      {
        "box": {
          "id": "d-277",
          "maxclass": "live.dial",
          "patching_rect": [
            600.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            273.0,
            40.0,
            42.0,
            42.0
          ],
          "varname": "master__d_277",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                2.5
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_dot_orbit_speed",
              "parameter_shortname": "Comet Spin",
              "parameter_mmax": 8.0,
              "parameter_mmin": 0.5,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-278",
          "maxclass": "live.comment",
          "patching_rect": [
            600.0,
            686.0,
            60.0,
            12.0
          ],
          "text": "Comet Spin",
          "presentation": 1,
          "presentation_rect": [
            268.0,
            84.0,
            52.0,
            12.0
          ],
          "varname": "master__lc_278",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Comet Spin"
        }
      },
      {
        "box": {
          "id": "n-279",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            740.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-280",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            766.0,
            200.0,
            22.0
          ],
          "text": "prepend knob master dot_orbit_speed"
        }
      },
      {
        "box": {
          "id": "d-281",
          "maxclass": "live.dial",
          "patching_rect": [
            636.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            325.0,
            40.0,
            42.0,
            42.0
          ],
          "varname": "master__d_281",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                14.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_trail_steps",
              "parameter_shortname": "Tail Length",
              "parameter_mmax": 40.0,
              "parameter_mmin": 4.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-282",
          "maxclass": "live.comment",
          "patching_rect": [
            636.0,
            686.0,
            60.0,
            12.0
          ],
          "text": "Tail Length",
          "presentation": 1,
          "presentation_rect": [
            320.0,
            84.0,
            52.0,
            12.0
          ],
          "varname": "master__lc_282",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Tail Length"
        }
      },
      {
        "box": {
          "id": "n-283",
          "maxclass": "newobj",
          "patching_rect": [
            636.0,
            740.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-284",
          "maxclass": "newobj",
          "patching_rect": [
            636.0,
            766.0,
            200.0,
            22.0
          ],
          "text": "prepend knob master trail_steps"
        }
      },
      {
        "box": {
          "id": "d-285",
          "maxclass": "live.dial",
          "patching_rect": [
            672.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            377.0,
            40.0,
            42.0,
            42.0
          ],
          "varname": "master__d_285",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.1
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_dot_speed_min",
              "parameter_shortname": "Speed Min",
              "parameter_mmax": 1.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-286",
          "maxclass": "live.comment",
          "patching_rect": [
            672.0,
            686.0,
            60.0,
            12.0
          ],
          "text": "Speed Min",
          "presentation": 1,
          "presentation_rect": [
            372.0,
            84.0,
            52.0,
            12.0
          ],
          "varname": "master__lc_286",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Speed Min"
        }
      },
      {
        "box": {
          "id": "n-287",
          "maxclass": "newobj",
          "patching_rect": [
            672.0,
            740.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-288",
          "maxclass": "newobj",
          "patching_rect": [
            672.0,
            766.0,
            200.0,
            22.0
          ],
          "text": "prepend knob master dot_speed_min"
        }
      },
      {
        "box": {
          "id": "d-289",
          "maxclass": "live.dial",
          "patching_rect": [
            708.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            429.0,
            40.0,
            42.0,
            42.0
          ],
          "varname": "master__d_289",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.3
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_dot_speed_max",
              "parameter_shortname": "Speed Max",
              "parameter_mmax": 2.5,
              "parameter_mmin": 0.3,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-290",
          "maxclass": "live.comment",
          "patching_rect": [
            708.0,
            686.0,
            60.0,
            12.0
          ],
          "text": "Speed Max",
          "presentation": 1,
          "presentation_rect": [
            424.0,
            84.0,
            52.0,
            12.0
          ],
          "varname": "master__lc_290",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Speed Max"
        }
      },
      {
        "box": {
          "id": "n-291",
          "maxclass": "newobj",
          "patching_rect": [
            708.0,
            740.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-292",
          "maxclass": "newobj",
          "patching_rect": [
            708.0,
            766.0,
            200.0,
            22.0
          ],
          "text": "prepend knob master dot_speed_max"
        }
      },
      {
        "box": {
          "id": "d-293",
          "maxclass": "live.dial",
          "patching_rect": [
            744.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            481.0,
            40.0,
            42.0,
            42.0
          ],
          "varname": "master__d_293",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.6
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_dot_speed_lock_exp",
              "parameter_shortname": "Speed Curve",
              "parameter_mmax": 4.0,
              "parameter_mmin": 0.3,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-294",
          "maxclass": "live.comment",
          "patching_rect": [
            744.0,
            686.0,
            60.0,
            12.0
          ],
          "text": "Speed Curve",
          "presentation": 1,
          "presentation_rect": [
            476.0,
            84.0,
            52.0,
            12.0
          ],
          "varname": "master__lc_294",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Speed Curve"
        }
      },
      {
        "box": {
          "id": "n-295",
          "maxclass": "newobj",
          "patching_rect": [
            744.0,
            740.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-296",
          "maxclass": "newobj",
          "patching_rect": [
            744.0,
            766.0,
            200.0,
            22.0
          ],
          "text": "prepend knob master dot_speed_lock_exp"
        }
      },
      {
        "box": {
          "id": "d-297",
          "maxclass": "live.dial",
          "patching_rect": [
            780.0,
            700.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            533.0,
            40.0,
            42.0,
            42.0
          ],
          "varname": "master__d_297",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.18
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_shimmer_intensity",
              "parameter_shortname": "Shimmer Amp",
              "parameter_mmax": 0.6,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-298",
          "maxclass": "live.comment",
          "patching_rect": [
            780.0,
            686.0,
            60.0,
            12.0
          ],
          "text": "Shimmer Amp",
          "presentation": 1,
          "presentation_rect": [
            528.0,
            84.0,
            52.0,
            12.0
          ],
          "varname": "master__lc_298",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Shimmer Amp"
        }
      },
      {
        "box": {
          "id": "n-299",
          "maxclass": "newobj",
          "patching_rect": [
            780.0,
            740.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-300",
          "maxclass": "newobj",
          "patching_rect": [
            780.0,
            766.0,
            200.0,
            22.0
          ],
          "text": "prepend knob master shimmer_intensity"
        }
      },
      {
        "box": {
          "id": "d-301",
          "maxclass": "live.dial",
          "patching_rect": [
            420.0,
            1080.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            14.0,
            40.0,
            44.0,
            44.0
          ],
          "varname": "physics__d_301",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                25.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_speed",
              "parameter_shortname": "Impulse Spe",
              "parameter_mmax": 80.0,
              "parameter_mmin": 5.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-302",
          "maxclass": "live.comment",
          "patching_rect": [
            420.0,
            1066.0,
            67.0,
            12.0
          ],
          "text": "Impulse Speed",
          "presentation": 1,
          "presentation_rect": [
            6.0,
            86.0,
            59.0,
            12.0
          ],
          "varname": "physics__lc_302",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Impulse Speed"
        }
      },
      {
        "box": {
          "id": "n-303",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            1120.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-304",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            1146.0,
            200.0,
            22.0
          ],
          "text": "prepend knob physics speed"
        }
      },
      {
        "box": {
          "id": "d-305",
          "maxclass": "live.dial",
          "patching_rect": [
            456.0,
            1080.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            72.0,
            40.0,
            44.0,
            44.0
          ],
          "varname": "physics__d_305",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.12
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_radial_offset",
              "parameter_shortname": "Jitter",
              "parameter_mmax": 0.6,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-306",
          "maxclass": "live.comment",
          "patching_rect": [
            456.0,
            1066.0,
            67.0,
            12.0
          ],
          "text": "Jitter",
          "presentation": 1,
          "presentation_rect": [
            65.0,
            86.0,
            59.0,
            12.0
          ],
          "varname": "physics__lc_306",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Jitter"
        }
      },
      {
        "box": {
          "id": "n-307",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            1120.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-308",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            1146.0,
            200.0,
            22.0
          ],
          "text": "prepend knob physics radial_offset"
        }
      },
      {
        "box": {
          "id": "d-309",
          "maxclass": "live.dial",
          "patching_rect": [
            492.0,
            1080.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            132.0,
            40.0,
            44.0,
            44.0
          ],
          "varname": "physics__d_309",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.35
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_squishiness",
              "parameter_shortname": "Squishiness",
              "parameter_mmax": 1.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-310",
          "maxclass": "live.comment",
          "patching_rect": [
            492.0,
            1066.0,
            67.0,
            12.0
          ],
          "text": "Squishiness",
          "presentation": 1,
          "presentation_rect": [
            124.0,
            86.0,
            59.0,
            12.0
          ],
          "varname": "physics__lc_310",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Squishiness"
        }
      },
      {
        "box": {
          "id": "n-311",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            1120.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-312",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            1146.0,
            200.0,
            22.0
          ],
          "text": "prepend knob physics squishiness"
        }
      },
      {
        "box": {
          "id": "d-313",
          "maxclass": "live.dial",
          "patching_rect": [
            528.0,
            1080.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            190.0,
            40.0,
            44.0,
            44.0
          ],
          "varname": "physics__d_313",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.3
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_damping",
              "parameter_shortname": "Viscosity",
              "parameter_mmax": 5.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-314",
          "maxclass": "live.comment",
          "patching_rect": [
            528.0,
            1066.0,
            67.0,
            12.0
          ],
          "text": "Viscosity",
          "presentation": 1,
          "presentation_rect": [
            183.0,
            86.0,
            59.0,
            12.0
          ],
          "varname": "physics__lc_314",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Viscosity"
        }
      },
      {
        "box": {
          "id": "n-315",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            1120.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-316",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            1146.0,
            200.0,
            22.0
          ],
          "text": "prepend knob physics damping"
        }
      },
      {
        "box": {
          "id": "d-317",
          "maxclass": "live.dial",
          "patching_rect": [
            564.0,
            1080.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            250.0,
            40.0,
            44.0,
            44.0
          ],
          "varname": "physics__d_317",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.75
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_bounce",
              "parameter_shortname": "Bounce",
              "parameter_mmax": 1.0,
              "parameter_mmin": 0.1,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-318",
          "maxclass": "live.comment",
          "patching_rect": [
            564.0,
            1066.0,
            67.0,
            12.0
          ],
          "text": "Bounce",
          "presentation": 1,
          "presentation_rect": [
            242.0,
            86.0,
            59.0,
            12.0
          ],
          "varname": "physics__lc_318",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Bounce"
        }
      },
      {
        "box": {
          "id": "n-319",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            1120.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-320",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            1146.0,
            200.0,
            22.0
          ],
          "text": "prepend knob physics bounce"
        }
      },
      {
        "box": {
          "id": "d-321",
          "maxclass": "live.dial",
          "patching_rect": [
            600.0,
            1080.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            308.0,
            40.0,
            44.0,
            44.0
          ],
          "varname": "physics__d_321",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                3.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_center_pull",
              "parameter_shortname": "Center Pull",
              "parameter_mmax": 15.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-322",
          "maxclass": "live.comment",
          "patching_rect": [
            600.0,
            1066.0,
            67.0,
            12.0
          ],
          "text": "Center Pull",
          "presentation": 1,
          "presentation_rect": [
            301.0,
            86.0,
            59.0,
            12.0
          ],
          "varname": "physics__lc_322",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Center Pull"
        }
      },
      {
        "box": {
          "id": "n-323",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            1120.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-324",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            1146.0,
            200.0,
            22.0
          ],
          "text": "prepend knob physics center_pull"
        }
      },
      {
        "box": {
          "id": "d-325",
          "maxclass": "live.dial",
          "patching_rect": [
            636.0,
            1080.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            368.0,
            40.0,
            44.0,
            44.0
          ],
          "varname": "physics__d_325",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.25
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_tau_squash",
              "parameter_shortname": "Squash \u03c4",
              "parameter_mmax": 1.0,
              "parameter_mmin": 0.05,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-326",
          "maxclass": "live.comment",
          "patching_rect": [
            636.0,
            1066.0,
            67.0,
            12.0
          ],
          "text": "Squash \u03c4",
          "presentation": 1,
          "presentation_rect": [
            360.0,
            86.0,
            59.0,
            12.0
          ],
          "varname": "physics__lc_326",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Squash \u03c4"
        }
      },
      {
        "box": {
          "id": "n-327",
          "maxclass": "newobj",
          "patching_rect": [
            636.0,
            1120.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-328",
          "maxclass": "newobj",
          "patching_rect": [
            636.0,
            1146.0,
            200.0,
            22.0
          ],
          "text": "prepend knob physics tau_squash"
        }
      },
      {
        "box": {
          "id": "d-329",
          "maxclass": "live.dial",
          "patching_rect": [
            672.0,
            1080.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            426.0,
            40.0,
            44.0,
            44.0
          ],
          "varname": "physics__d_329",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                40.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_max_velocity",
              "parameter_shortname": "Max Velocit",
              "parameter_mmax": 120.0,
              "parameter_mmin": 10.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-330",
          "maxclass": "live.comment",
          "patching_rect": [
            672.0,
            1066.0,
            67.0,
            12.0
          ],
          "text": "Max Velocity",
          "presentation": 1,
          "presentation_rect": [
            419.0,
            86.0,
            59.0,
            12.0
          ],
          "varname": "physics__lc_330",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Max Velocity"
        }
      },
      {
        "box": {
          "id": "n-331",
          "maxclass": "newobj",
          "patching_rect": [
            672.0,
            1120.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-332",
          "maxclass": "newobj",
          "patching_rect": [
            672.0,
            1146.0,
            200.0,
            22.0
          ],
          "text": "prepend knob physics max_velocity"
        }
      },
      {
        "box": {
          "id": "d-333",
          "maxclass": "live.dial",
          "patching_rect": [
            708.0,
            1080.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            486.0,
            40.0,
            44.0,
            44.0
          ],
          "varname": "physics__d_333",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.6
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_angular_friction",
              "parameter_shortname": "Rot Frictio",
              "parameter_mmax": 4.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-334",
          "maxclass": "live.comment",
          "patching_rect": [
            708.0,
            1066.0,
            67.0,
            12.0
          ],
          "text": "Rot Friction",
          "presentation": 1,
          "presentation_rect": [
            478.0,
            86.0,
            59.0,
            12.0
          ],
          "varname": "physics__lc_334",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Rot Friction"
        }
      },
      {
        "box": {
          "id": "n-335",
          "maxclass": "newobj",
          "patching_rect": [
            708.0,
            1120.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-336",
          "maxclass": "newobj",
          "patching_rect": [
            708.0,
            1146.0,
            200.0,
            22.0
          ],
          "text": "prepend knob physics angular_friction"
        }
      },
      {
        "box": {
          "id": "d-337",
          "maxclass": "live.dial",
          "patching_rect": [
            744.0,
            1080.0,
            24.0,
            36.0
          ],
          "presentation": 1,
          "presentation_rect": [
            544.0,
            40.0,
            44.0,
            44.0
          ],
          "varname": "physics__d_337",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.35
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_phys_squash_damping",
              "parameter_shortname": "Squash \u03b6",
              "parameter_mmax": 1.5,
              "parameter_mmin": 0.05,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "lc-338",
          "maxclass": "live.comment",
          "patching_rect": [
            744.0,
            1066.0,
            67.0,
            12.0
          ],
          "text": "Squash \u03b6",
          "presentation": 1,
          "presentation_rect": [
            537.0,
            86.0,
            59.0,
            12.0
          ],
          "varname": "physics__lc_338",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Squash \u03b6"
        }
      },
      {
        "box": {
          "id": "n-339",
          "maxclass": "newobj",
          "patching_rect": [
            744.0,
            1120.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-340",
          "maxclass": "newobj",
          "patching_rect": [
            744.0,
            1146.0,
            200.0,
            22.0
          ],
          "text": "prepend knob physics squash_damping"
        }
      },
      {
        "box": {
          "id": "lc-341",
          "maxclass": "live.comment",
          "patching_rect": [
            420.0,
            782.0,
            60.0,
            12.0
          ],
          "text": "Skew",
          "presentation": 1,
          "presentation_rect": [
            64.0,
            28.0,
            84.0,
            11.0
          ],
          "varname": "rings__lc_341",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "lc-342",
          "maxclass": "live.comment",
          "patching_rect": [
            456.0,
            782.0,
            60.0,
            12.0
          ],
          "text": "Phase",
          "presentation": 1,
          "presentation_rect": [
            148.0,
            28.0,
            84.0,
            11.0
          ],
          "varname": "rings__lc_342",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "lc-343",
          "maxclass": "live.comment",
          "patching_rect": [
            492.0,
            782.0,
            60.0,
            12.0
          ],
          "text": "Blur",
          "presentation": 1,
          "presentation_rect": [
            232.0,
            28.0,
            84.0,
            11.0
          ],
          "varname": "rings__lc_343",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "lc-344",
          "maxclass": "live.comment",
          "patching_rect": [
            528.0,
            782.0,
            60.0,
            12.0
          ],
          "text": "Scale",
          "presentation": 1,
          "presentation_rect": [
            316.0,
            28.0,
            84.0,
            11.0
          ],
          "varname": "rings__lc_344",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "lc-345",
          "maxclass": "live.comment",
          "patching_rect": [
            564.0,
            782.0,
            60.0,
            12.0
          ],
          "text": "Dash",
          "presentation": 1,
          "presentation_rect": [
            400.0,
            28.0,
            84.0,
            11.0
          ],
          "varname": "rings__lc_345",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "lc-346",
          "maxclass": "live.comment",
          "patching_rect": [
            600.0,
            782.0,
            60.0,
            12.0
          ],
          "text": "Gap",
          "presentation": 1,
          "presentation_rect": [
            484.0,
            28.0,
            84.0,
            11.0
          ],
          "varname": "rings__lc_346",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "lc-347",
          "maxclass": "live.comment",
          "patching_rect": [
            360.0,
            800.0,
            56.0,
            14.0
          ],
          "text": "Outer",
          "presentation": 1,
          "presentation_rect": [
            6.0,
            54.0,
            56.0,
            12.0
          ],
          "varname": "rings__lc_347",
          "fontsize": 8.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Outer ring"
        }
      },
      {
        "box": {
          "id": "d-348",
          "maxclass": "live.dial",
          "patching_rect": [
            420.0,
            800.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            90.0,
            44.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_348",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.12
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_skew_0",
              "parameter_shortname": "O Skew",
              "parameter_mmax": 0.5,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-349",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            822.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-350",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            848.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 0 skew"
        }
      },
      {
        "box": {
          "id": "d-351",
          "maxclass": "live.dial",
          "patching_rect": [
            456.0,
            800.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            174.0,
            44.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_351",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_phase_0",
              "parameter_shortname": "O Phase",
              "parameter_mmax": 3.14159,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-352",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            822.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-353",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            848.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 0 phase"
        }
      },
      {
        "box": {
          "id": "d-354",
          "maxclass": "live.dial",
          "patching_rect": [
            492.0,
            800.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            258.0,
            44.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_354",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.8
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_blur_0",
              "parameter_shortname": "O Blur",
              "parameter_mmax": 8.0,
              "parameter_mmin": 0.3,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-355",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            822.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-356",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            848.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 0 blur"
        }
      },
      {
        "box": {
          "id": "d-357",
          "maxclass": "live.dial",
          "patching_rect": [
            528.0,
            800.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            342.0,
            44.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_357",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_radius_scale_0",
              "parameter_shortname": "O Scale",
              "parameter_mmax": 2.0,
              "parameter_mmin": 0.2,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-358",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            822.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-359",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            848.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 0 radius_scale"
        }
      },
      {
        "box": {
          "id": "d-360",
          "maxclass": "live.dial",
          "patching_rect": [
            564.0,
            800.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            426.0,
            44.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_360",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_segments_0",
              "parameter_shortname": "O Dash",
              "parameter_mmax": 32.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-361",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            822.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-362",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            848.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 0 segments"
        }
      },
      {
        "box": {
          "id": "d-363",
          "maxclass": "live.dial",
          "patching_rect": [
            600.0,
            800.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            510.0,
            44.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_363",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.4
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_gap_0",
              "parameter_shortname": "O Gap",
              "parameter_mmax": 0.95,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-364",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            822.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-365",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            848.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 0 gap"
        }
      },
      {
        "box": {
          "id": "lc-366",
          "maxclass": "live.comment",
          "patching_rect": [
            360.0,
            880.0,
            56.0,
            14.0
          ],
          "text": "Middle",
          "presentation": 1,
          "presentation_rect": [
            6.0,
            87.0,
            56.0,
            12.0
          ],
          "varname": "rings__lc_366",
          "fontsize": 8.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Middle ring"
        }
      },
      {
        "box": {
          "id": "d-367",
          "maxclass": "live.dial",
          "patching_rect": [
            420.0,
            880.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            90.0,
            77.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_367",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.18
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_skew_1",
              "parameter_shortname": "M Skew",
              "parameter_mmax": 0.5,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-368",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            902.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-369",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            928.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 1 skew"
        }
      },
      {
        "box": {
          "id": "d-370",
          "maxclass": "live.dial",
          "patching_rect": [
            456.0,
            880.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            174.0,
            77.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_370",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_phase_1",
              "parameter_shortname": "M Phase",
              "parameter_mmax": 3.14159,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-371",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            902.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-372",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            928.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 1 phase"
        }
      },
      {
        "box": {
          "id": "d-373",
          "maxclass": "live.dial",
          "patching_rect": [
            492.0,
            880.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            258.0,
            77.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_373",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                2.5
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_blur_1",
              "parameter_shortname": "M Blur",
              "parameter_mmax": 8.0,
              "parameter_mmin": 0.3,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-374",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            902.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-375",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            928.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 1 blur"
        }
      },
      {
        "box": {
          "id": "d-376",
          "maxclass": "live.dial",
          "patching_rect": [
            528.0,
            880.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            342.0,
            77.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_376",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_radius_scale_1",
              "parameter_shortname": "M Scale",
              "parameter_mmax": 2.0,
              "parameter_mmin": 0.2,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-377",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            902.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-378",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            928.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 1 radius_scale"
        }
      },
      {
        "box": {
          "id": "d-379",
          "maxclass": "live.dial",
          "patching_rect": [
            564.0,
            880.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            426.0,
            77.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_379",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_segments_1",
              "parameter_shortname": "M Dash",
              "parameter_mmax": 32.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-380",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            902.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-381",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            928.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 1 segments"
        }
      },
      {
        "box": {
          "id": "d-382",
          "maxclass": "live.dial",
          "patching_rect": [
            600.0,
            880.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            510.0,
            77.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_382",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.4
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_gap_1",
              "parameter_shortname": "M Gap",
              "parameter_mmax": 0.95,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-383",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            902.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-384",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            928.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 1 gap"
        }
      },
      {
        "box": {
          "id": "lc-385",
          "maxclass": "live.comment",
          "patching_rect": [
            360.0,
            960.0,
            56.0,
            14.0
          ],
          "text": "Inner",
          "presentation": 1,
          "presentation_rect": [
            6.0,
            120.0,
            56.0,
            12.0
          ],
          "varname": "rings__lc_385",
          "fontsize": 8.0,
          "numinlets": 1,
          "numoutlets": 0,
          "hint": "Inner ring"
        }
      },
      {
        "box": {
          "id": "d-386",
          "maxclass": "live.dial",
          "patching_rect": [
            420.0,
            960.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            90.0,
            110.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_386",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.2
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_skew_2",
              "parameter_shortname": "I Skew",
              "parameter_mmax": 0.5,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-387",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            982.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-388",
          "maxclass": "newobj",
          "patching_rect": [
            420.0,
            1008.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 2 skew"
        }
      },
      {
        "box": {
          "id": "d-389",
          "maxclass": "live.dial",
          "patching_rect": [
            456.0,
            960.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            174.0,
            110.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_389",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                2.1
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_phase_2",
              "parameter_shortname": "I Phase",
              "parameter_mmax": 3.14159,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-390",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            982.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-391",
          "maxclass": "newobj",
          "patching_rect": [
            456.0,
            1008.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 2 phase"
        }
      },
      {
        "box": {
          "id": "d-392",
          "maxclass": "live.dial",
          "patching_rect": [
            492.0,
            960.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            258.0,
            110.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_392",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.2
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_blur_2",
              "parameter_shortname": "I Blur",
              "parameter_mmax": 8.0,
              "parameter_mmin": 0.3,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-393",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            982.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-394",
          "maxclass": "newobj",
          "patching_rect": [
            492.0,
            1008.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 2 blur"
        }
      },
      {
        "box": {
          "id": "d-395",
          "maxclass": "live.dial",
          "patching_rect": [
            528.0,
            960.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            342.0,
            110.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_395",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                1.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_radius_scale_2",
              "parameter_shortname": "I Scale",
              "parameter_mmax": 2.0,
              "parameter_mmin": 0.2,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-396",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            982.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-397",
          "maxclass": "newobj",
          "patching_rect": [
            528.0,
            1008.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 2 radius_scale"
        }
      },
      {
        "box": {
          "id": "d-398",
          "maxclass": "live.dial",
          "patching_rect": [
            564.0,
            960.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            426.0,
            110.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_398",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_segments_2",
              "parameter_shortname": "I Dash",
              "parameter_mmax": 32.0,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-399",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            982.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-400",
          "maxclass": "newobj",
          "patching_rect": [
            564.0,
            1008.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 2 segments"
        }
      },
      {
        "box": {
          "id": "d-401",
          "maxclass": "live.dial",
          "patching_rect": [
            600.0,
            960.0,
            22.0,
            18.0
          ],
          "presentation": 1,
          "presentation_rect": [
            510.0,
            110.0,
            32.0,
            32.0
          ],
          "varname": "rings__d_401",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": [
            "",
            "float"
          ],
          "parameter_enable": 1,
          "showname": 0,
          "shownumber": 0,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0.4
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_oval_gap_2",
              "parameter_shortname": "I Gap",
              "parameter_mmax": 0.95,
              "parameter_mmin": 0.0,
              "parameter_type": 0,
              "parameter_unitstyle": 1,
              "parameter_exponent": 1.0,
              "parameter_modmode": 2,
              "parameter_steps": 0,
              "parameter_speedlim": 0.0,
              "parameter_linknames": 1
            }
          }
        }
      },
      {
        "box": {
          "id": "n-402",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            982.0,
            60.0,
            22.0
          ],
          "text": "change"
        }
      },
      {
        "box": {
          "id": "n-403",
          "maxclass": "newobj",
          "patching_rect": [
            600.0,
            1008.0,
            200.0,
            22.0
          ],
          "text": "prepend knob oval 2 gap"
        }
      },
      {
        "box": {
          "id": "lc-404",
          "maxclass": "live.comment",
          "patching_rect": [
            760.0,
            40.0,
            60.0,
            14.0
          ],
          "text": "host",
          "presentation": 1,
          "presentation_rect": [
            8.0,
            36.0,
            32.0,
            14.0
          ],
          "varname": "conn__lc_404",
          "fontsize": 9.0,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "te-405",
          "maxclass": "textedit",
          "patching_rect": [
            760.0,
            70.0,
            120.0,
            22.0
          ],
          "text": "here.local",
          "presentation": 1,
          "presentation_rect": [
            46.0,
            34.0,
            220.0,
            18.0
          ],
          "varname": "conn__te_405",
          "keymode": 1,
          "numinlets": 1,
          "numoutlets": 4,
          "outlettype": [
            "",
            "int",
            "",
            ""
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                "here.local"
              ],
              "parameter_initial_enable": 1,
              "parameter_invisible": 1,
              "parameter_longname": "here_host",
              "parameter_shortname": "here_host",
              "parameter_type": 3
            }
          }
        }
      },
      {
        "box": {
          "id": "n-406",
          "maxclass": "newobj",
          "patching_rect": [
            760.0,
            100.0,
            100.0,
            22.0
          ],
          "text": "route text"
        }
      },
      {
        "box": {
          "id": "n-407",
          "maxclass": "newobj",
          "patching_rect": [
            760.0,
            130.0,
            100.0,
            22.0
          ],
          "text": "prepend host"
        }
      },
      {
        "box": {
          "id": "lc-408",
          "maxclass": "live.comment",
          "patching_rect": [
            760.0,
            160.0,
            60.0,
            14.0
          ],
          "text": "port",
          "presentation": 1,
          "presentation_rect": [
            8.0,
            64.0,
            32.0,
            14.0
          ],
          "varname": "conn__lc_408",
          "fontsize": 9.0,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "te-409",
          "maxclass": "textedit",
          "patching_rect": [
            760.0,
            190.0,
            120.0,
            22.0
          ],
          "text": "9000",
          "presentation": 1,
          "presentation_rect": [
            46.0,
            62.0,
            90.0,
            18.0
          ],
          "varname": "conn__te_409",
          "keymode": 1,
          "numinlets": 1,
          "numoutlets": 4,
          "outlettype": [
            "",
            "int",
            "",
            ""
          ],
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                9000
              ],
              "parameter_initial_enable": 1,
              "parameter_invisible": 1,
              "parameter_longname": "here_port",
              "parameter_shortname": "here_port",
              "parameter_type": 3
            }
          }
        }
      },
      {
        "box": {
          "id": "n-410",
          "maxclass": "newobj",
          "patching_rect": [
            760.0,
            220.0,
            100.0,
            22.0
          ],
          "text": "route text"
        }
      },
      {
        "box": {
          "id": "n-411",
          "maxclass": "newobj",
          "patching_rect": [
            760.0,
            250.0,
            100.0,
            22.0
          ],
          "text": "prepend port"
        }
      },
      {
        "box": {
          "id": "b-412",
          "maxclass": "live.button",
          "patching_rect": [
            760.0,
            290.0,
            24.0,
            24.0
          ],
          "presentation": 1,
          "presentation_rect": [
            8.0,
            92.0,
            22.0,
            18.0
          ],
          "varname": "conn__b_412",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "here_test",
              "parameter_shortname": "test",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "m-413",
          "maxclass": "message",
          "patching_rect": [
            760.0,
            320.0,
            100.0,
            22.0
          ],
          "text": "palette 0",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "lc-414",
          "maxclass": "live.comment",
          "patching_rect": [
            790.0,
            290.0,
            60.0,
            14.0
          ],
          "text": "ping  \u00b7  sends a palette swap so you can confirm the bench is listening",
          "presentation": 1,
          "presentation_rect": [
            36.0,
            94.0,
            440.0,
            14.0
          ],
          "varname": "conn__lc_414",
          "fontsize": 8.0,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "tog-415",
          "maxclass": "live.toggle",
          "patching_rect": [
            760.0,
            350.0,
            24.0,
            24.0
          ],
          "presentation": 1,
          "presentation_rect": [
            8.0,
            120.0,
            18.0,
            18.0
          ],
          "varname": "conn__tog_415",
          "numinlets": 1,
          "numoutlets": 1,
          "parameter_enable": 1,
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_initial": [
                0
              ],
              "parameter_initial_enable": 1,
              "parameter_longname": "here_debug",
              "parameter_shortname": "debug",
              "parameter_type": 2
            }
          }
        }
      },
      {
        "box": {
          "id": "n-416",
          "maxclass": "newobj",
          "patching_rect": [
            760.0,
            380.0,
            80.0,
            22.0
          ],
          "text": "gate 1 0"
        }
      },
      {
        "box": {
          "id": "n-417",
          "maxclass": "newobj",
          "patching_rect": [
            760.0,
            410.0,
            80.0,
            22.0
          ],
          "text": "print HERE"
        }
      },
      {
        "box": {
          "id": "lc-418",
          "maxclass": "live.comment",
          "patching_rect": [
            790.0,
            350.0,
            60.0,
            14.0
          ],
          "text": "debug  \u00b7  print every outgoing OSC message to the Max console",
          "presentation": 1,
          "presentation_rect": [
            36.0,
            122.0,
            440.0,
            14.0
          ],
          "varname": "conn__lc_418",
          "fontsize": 8.0,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "lc-419",
          "maxclass": "live.comment",
          "patching_rect": [
            760.0,
            450.0,
            200.0,
            14.0
          ],
          "text": "MIDI notes 36\u201375 \u2192 events  \u00b7  knobs \u2192 live params",
          "presentation": 1,
          "presentation_rect": [
            8.0,
            150.0,
            470.0,
            12.0
          ],
          "varname": "conn__lc_419",
          "fontsize": 7.5,
          "numinlets": 1,
          "numoutlets": 0
        }
      },
      {
        "box": {
          "id": "n-420",
          "maxclass": "newobj",
          "patching_rect": [
            1000.0,
            240.0,
            90.0,
            22.0
          ],
          "text": "thispatcher"
        }
      },
      {
        "box": {
          "id": "n-421",
          "maxclass": "newobj",
          "patching_rect": [
            1000.0,
            80.0,
            120.0,
            22.0
          ],
          "text": "sel 0 1 2 3 4 5"
        }
      },
      {
        "box": {
          "id": "m-422",
          "maxclass": "message",
          "patching_rect": [
            1000.0,
            130.0,
            200.0,
            22.0
          ],
          "text": "script show midi1__t_11, script show midi1__lc_12, script show midi1__t_17, script show midi1__lc_18, script show midi1__t_23, script show midi1__lc_24, script show midi1__t_29, script show midi1__lc_30, script show midi1__t_35, script show midi1__lc_36, script show midi1__t_41, script show midi1__lc_42, script show midi1__t_47, script show midi1__lc_48, script show midi1__t_53, script show midi1__lc_54, script show midi1__t_59, script show midi1__lc_60, script show midi1__t_65, script show midi1__lc_66, script show midi1__t_71, script show midi1__lc_72, script show midi1__t_77, script show midi1__lc_78, script show midi1__t_83, script show midi1__lc_84, script show midi1__t_89, script show midi1__lc_90, script show midi1__t_95, script show midi1__lc_96, script show midi1__t_101, script show midi1__lc_102, script show midi1__t_107, script show midi1__lc_108, script hide midi2__t_113, script hide midi2__lc_114, script hide midi2__t_119, script hide midi2__lc_120, script hide midi2__t_125, script hide midi2__lc_126, script hide midi2__t_131, script hide midi2__lc_132, script hide midi2__t_137, script hide midi2__lc_138, script hide midi2__t_143, script hide midi2__lc_144, script hide midi2__t_149, script hide midi2__lc_150, script hide midi2__t_155, script hide midi2__lc_156, script hide midi2__t_161, script hide midi2__lc_162, script hide midi2__t_167, script hide midi2__lc_168, script hide midi2__t_173, script hide midi2__lc_174, script hide midi2__t_179, script hide midi2__lc_180, script hide midi2__t_185, script hide midi2__lc_186, script hide midi2__t_191, script hide midi2__lc_192, script hide midi2__t_197, script hide midi2__lc_198, script hide midi2__t_203, script hide midi2__lc_204, script hide midi2__t_209, script hide midi2__lc_210, script hide midi2__t_215, script hide midi2__lc_216, script hide midi2__t_221, script hide midi2__lc_222, script hide midi2__t_227, script hide midi2__lc_228, script hide midi2__t_233, script hide midi2__lc_234, script hide midi2__t_239, script hide midi2__lc_240, script hide midi2__t_245, script hide midi2__lc_246, script hide midi2__t_251, script hide midi2__lc_252, script hide master__d_257, script hide master__lc_258, script hide master__d_261, script hide master__lc_262, script hide master__d_265, script hide master__lc_266, script hide master__d_269, script hide master__lc_270, script hide master__d_273, script hide master__lc_274, script hide master__d_277, script hide master__lc_278, script hide master__d_281, script hide master__lc_282, script hide master__d_285, script hide master__lc_286, script hide master__d_289, script hide master__lc_290, script hide master__d_293, script hide master__lc_294, script hide master__d_297, script hide master__lc_298, script hide rings__lc_341, script hide rings__lc_342, script hide rings__lc_343, script hide rings__lc_344, script hide rings__lc_345, script hide rings__lc_346, script hide rings__lc_347, script hide rings__d_348, script hide rings__d_351, script hide rings__d_354, script hide rings__d_357, script hide rings__d_360, script hide rings__d_363, script hide rings__lc_366, script hide rings__d_367, script hide rings__d_370, script hide rings__d_373, script hide rings__d_376, script hide rings__d_379, script hide rings__d_382, script hide rings__lc_385, script hide rings__d_386, script hide rings__d_389, script hide rings__d_392, script hide rings__d_395, script hide rings__d_398, script hide rings__d_401, script hide physics__d_301, script hide physics__lc_302, script hide physics__d_305, script hide physics__lc_306, script hide physics__d_309, script hide physics__lc_310, script hide physics__d_313, script hide physics__lc_314, script hide physics__d_317, script hide physics__lc_318, script hide physics__d_321, script hide physics__lc_322, script hide physics__d_325, script hide physics__lc_326, script hide physics__d_329, script hide physics__lc_330, script hide physics__d_333, script hide physics__lc_334, script hide physics__d_337, script hide physics__lc_338, script hide conn__lc_404, script hide conn__te_405, script hide conn__lc_408, script hide conn__te_409, script hide conn__b_412, script hide conn__lc_414, script hide conn__tog_415, script hide conn__lc_418, script hide conn__lc_419",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-423",
          "maxclass": "message",
          "patching_rect": [
            1210.0,
            130.0,
            200.0,
            22.0
          ],
          "text": "script show midi2__t_113, script show midi2__lc_114, script show midi2__t_119, script show midi2__lc_120, script show midi2__t_125, script show midi2__lc_126, script show midi2__t_131, script show midi2__lc_132, script show midi2__t_137, script show midi2__lc_138, script show midi2__t_143, script show midi2__lc_144, script show midi2__t_149, script show midi2__lc_150, script show midi2__t_155, script show midi2__lc_156, script show midi2__t_161, script show midi2__lc_162, script show midi2__t_167, script show midi2__lc_168, script show midi2__t_173, script show midi2__lc_174, script show midi2__t_179, script show midi2__lc_180, script show midi2__t_185, script show midi2__lc_186, script show midi2__t_191, script show midi2__lc_192, script show midi2__t_197, script show midi2__lc_198, script show midi2__t_203, script show midi2__lc_204, script show midi2__t_209, script show midi2__lc_210, script show midi2__t_215, script show midi2__lc_216, script show midi2__t_221, script show midi2__lc_222, script show midi2__t_227, script show midi2__lc_228, script show midi2__t_233, script show midi2__lc_234, script show midi2__t_239, script show midi2__lc_240, script show midi2__t_245, script show midi2__lc_246, script show midi2__t_251, script show midi2__lc_252, script hide midi1__t_11, script hide midi1__lc_12, script hide midi1__t_17, script hide midi1__lc_18, script hide midi1__t_23, script hide midi1__lc_24, script hide midi1__t_29, script hide midi1__lc_30, script hide midi1__t_35, script hide midi1__lc_36, script hide midi1__t_41, script hide midi1__lc_42, script hide midi1__t_47, script hide midi1__lc_48, script hide midi1__t_53, script hide midi1__lc_54, script hide midi1__t_59, script hide midi1__lc_60, script hide midi1__t_65, script hide midi1__lc_66, script hide midi1__t_71, script hide midi1__lc_72, script hide midi1__t_77, script hide midi1__lc_78, script hide midi1__t_83, script hide midi1__lc_84, script hide midi1__t_89, script hide midi1__lc_90, script hide midi1__t_95, script hide midi1__lc_96, script hide midi1__t_101, script hide midi1__lc_102, script hide midi1__t_107, script hide midi1__lc_108, script hide master__d_257, script hide master__lc_258, script hide master__d_261, script hide master__lc_262, script hide master__d_265, script hide master__lc_266, script hide master__d_269, script hide master__lc_270, script hide master__d_273, script hide master__lc_274, script hide master__d_277, script hide master__lc_278, script hide master__d_281, script hide master__lc_282, script hide master__d_285, script hide master__lc_286, script hide master__d_289, script hide master__lc_290, script hide master__d_293, script hide master__lc_294, script hide master__d_297, script hide master__lc_298, script hide rings__lc_341, script hide rings__lc_342, script hide rings__lc_343, script hide rings__lc_344, script hide rings__lc_345, script hide rings__lc_346, script hide rings__lc_347, script hide rings__d_348, script hide rings__d_351, script hide rings__d_354, script hide rings__d_357, script hide rings__d_360, script hide rings__d_363, script hide rings__lc_366, script hide rings__d_367, script hide rings__d_370, script hide rings__d_373, script hide rings__d_376, script hide rings__d_379, script hide rings__d_382, script hide rings__lc_385, script hide rings__d_386, script hide rings__d_389, script hide rings__d_392, script hide rings__d_395, script hide rings__d_398, script hide rings__d_401, script hide physics__d_301, script hide physics__lc_302, script hide physics__d_305, script hide physics__lc_306, script hide physics__d_309, script hide physics__lc_310, script hide physics__d_313, script hide physics__lc_314, script hide physics__d_317, script hide physics__lc_318, script hide physics__d_321, script hide physics__lc_322, script hide physics__d_325, script hide physics__lc_326, script hide physics__d_329, script hide physics__lc_330, script hide physics__d_333, script hide physics__lc_334, script hide physics__d_337, script hide physics__lc_338, script hide conn__lc_404, script hide conn__te_405, script hide conn__lc_408, script hide conn__te_409, script hide conn__b_412, script hide conn__lc_414, script hide conn__tog_415, script hide conn__lc_418, script hide conn__lc_419",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-424",
          "maxclass": "message",
          "patching_rect": [
            1420.0,
            130.0,
            200.0,
            22.0
          ],
          "text": "script show master__d_257, script show master__lc_258, script show master__d_261, script show master__lc_262, script show master__d_265, script show master__lc_266, script show master__d_269, script show master__lc_270, script show master__d_273, script show master__lc_274, script show master__d_277, script show master__lc_278, script show master__d_281, script show master__lc_282, script show master__d_285, script show master__lc_286, script show master__d_289, script show master__lc_290, script show master__d_293, script show master__lc_294, script show master__d_297, script show master__lc_298, script hide midi1__t_11, script hide midi1__lc_12, script hide midi1__t_17, script hide midi1__lc_18, script hide midi1__t_23, script hide midi1__lc_24, script hide midi1__t_29, script hide midi1__lc_30, script hide midi1__t_35, script hide midi1__lc_36, script hide midi1__t_41, script hide midi1__lc_42, script hide midi1__t_47, script hide midi1__lc_48, script hide midi1__t_53, script hide midi1__lc_54, script hide midi1__t_59, script hide midi1__lc_60, script hide midi1__t_65, script hide midi1__lc_66, script hide midi1__t_71, script hide midi1__lc_72, script hide midi1__t_77, script hide midi1__lc_78, script hide midi1__t_83, script hide midi1__lc_84, script hide midi1__t_89, script hide midi1__lc_90, script hide midi1__t_95, script hide midi1__lc_96, script hide midi1__t_101, script hide midi1__lc_102, script hide midi1__t_107, script hide midi1__lc_108, script hide midi2__t_113, script hide midi2__lc_114, script hide midi2__t_119, script hide midi2__lc_120, script hide midi2__t_125, script hide midi2__lc_126, script hide midi2__t_131, script hide midi2__lc_132, script hide midi2__t_137, script hide midi2__lc_138, script hide midi2__t_143, script hide midi2__lc_144, script hide midi2__t_149, script hide midi2__lc_150, script hide midi2__t_155, script hide midi2__lc_156, script hide midi2__t_161, script hide midi2__lc_162, script hide midi2__t_167, script hide midi2__lc_168, script hide midi2__t_173, script hide midi2__lc_174, script hide midi2__t_179, script hide midi2__lc_180, script hide midi2__t_185, script hide midi2__lc_186, script hide midi2__t_191, script hide midi2__lc_192, script hide midi2__t_197, script hide midi2__lc_198, script hide midi2__t_203, script hide midi2__lc_204, script hide midi2__t_209, script hide midi2__lc_210, script hide midi2__t_215, script hide midi2__lc_216, script hide midi2__t_221, script hide midi2__lc_222, script hide midi2__t_227, script hide midi2__lc_228, script hide midi2__t_233, script hide midi2__lc_234, script hide midi2__t_239, script hide midi2__lc_240, script hide midi2__t_245, script hide midi2__lc_246, script hide midi2__t_251, script hide midi2__lc_252, script hide rings__lc_341, script hide rings__lc_342, script hide rings__lc_343, script hide rings__lc_344, script hide rings__lc_345, script hide rings__lc_346, script hide rings__lc_347, script hide rings__d_348, script hide rings__d_351, script hide rings__d_354, script hide rings__d_357, script hide rings__d_360, script hide rings__d_363, script hide rings__lc_366, script hide rings__d_367, script hide rings__d_370, script hide rings__d_373, script hide rings__d_376, script hide rings__d_379, script hide rings__d_382, script hide rings__lc_385, script hide rings__d_386, script hide rings__d_389, script hide rings__d_392, script hide rings__d_395, script hide rings__d_398, script hide rings__d_401, script hide physics__d_301, script hide physics__lc_302, script hide physics__d_305, script hide physics__lc_306, script hide physics__d_309, script hide physics__lc_310, script hide physics__d_313, script hide physics__lc_314, script hide physics__d_317, script hide physics__lc_318, script hide physics__d_321, script hide physics__lc_322, script hide physics__d_325, script hide physics__lc_326, script hide physics__d_329, script hide physics__lc_330, script hide physics__d_333, script hide physics__lc_334, script hide physics__d_337, script hide physics__lc_338, script hide conn__lc_404, script hide conn__te_405, script hide conn__lc_408, script hide conn__te_409, script hide conn__b_412, script hide conn__lc_414, script hide conn__tog_415, script hide conn__lc_418, script hide conn__lc_419",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-425",
          "maxclass": "message",
          "patching_rect": [
            1630.0,
            130.0,
            200.0,
            22.0
          ],
          "text": "script show rings__lc_341, script show rings__lc_342, script show rings__lc_343, script show rings__lc_344, script show rings__lc_345, script show rings__lc_346, script show rings__lc_347, script show rings__d_348, script show rings__d_351, script show rings__d_354, script show rings__d_357, script show rings__d_360, script show rings__d_363, script show rings__lc_366, script show rings__d_367, script show rings__d_370, script show rings__d_373, script show rings__d_376, script show rings__d_379, script show rings__d_382, script show rings__lc_385, script show rings__d_386, script show rings__d_389, script show rings__d_392, script show rings__d_395, script show rings__d_398, script show rings__d_401, script hide midi1__t_11, script hide midi1__lc_12, script hide midi1__t_17, script hide midi1__lc_18, script hide midi1__t_23, script hide midi1__lc_24, script hide midi1__t_29, script hide midi1__lc_30, script hide midi1__t_35, script hide midi1__lc_36, script hide midi1__t_41, script hide midi1__lc_42, script hide midi1__t_47, script hide midi1__lc_48, script hide midi1__t_53, script hide midi1__lc_54, script hide midi1__t_59, script hide midi1__lc_60, script hide midi1__t_65, script hide midi1__lc_66, script hide midi1__t_71, script hide midi1__lc_72, script hide midi1__t_77, script hide midi1__lc_78, script hide midi1__t_83, script hide midi1__lc_84, script hide midi1__t_89, script hide midi1__lc_90, script hide midi1__t_95, script hide midi1__lc_96, script hide midi1__t_101, script hide midi1__lc_102, script hide midi1__t_107, script hide midi1__lc_108, script hide midi2__t_113, script hide midi2__lc_114, script hide midi2__t_119, script hide midi2__lc_120, script hide midi2__t_125, script hide midi2__lc_126, script hide midi2__t_131, script hide midi2__lc_132, script hide midi2__t_137, script hide midi2__lc_138, script hide midi2__t_143, script hide midi2__lc_144, script hide midi2__t_149, script hide midi2__lc_150, script hide midi2__t_155, script hide midi2__lc_156, script hide midi2__t_161, script hide midi2__lc_162, script hide midi2__t_167, script hide midi2__lc_168, script hide midi2__t_173, script hide midi2__lc_174, script hide midi2__t_179, script hide midi2__lc_180, script hide midi2__t_185, script hide midi2__lc_186, script hide midi2__t_191, script hide midi2__lc_192, script hide midi2__t_197, script hide midi2__lc_198, script hide midi2__t_203, script hide midi2__lc_204, script hide midi2__t_209, script hide midi2__lc_210, script hide midi2__t_215, script hide midi2__lc_216, script hide midi2__t_221, script hide midi2__lc_222, script hide midi2__t_227, script hide midi2__lc_228, script hide midi2__t_233, script hide midi2__lc_234, script hide midi2__t_239, script hide midi2__lc_240, script hide midi2__t_245, script hide midi2__lc_246, script hide midi2__t_251, script hide midi2__lc_252, script hide master__d_257, script hide master__lc_258, script hide master__d_261, script hide master__lc_262, script hide master__d_265, script hide master__lc_266, script hide master__d_269, script hide master__lc_270, script hide master__d_273, script hide master__lc_274, script hide master__d_277, script hide master__lc_278, script hide master__d_281, script hide master__lc_282, script hide master__d_285, script hide master__lc_286, script hide master__d_289, script hide master__lc_290, script hide master__d_293, script hide master__lc_294, script hide master__d_297, script hide master__lc_298, script hide physics__d_301, script hide physics__lc_302, script hide physics__d_305, script hide physics__lc_306, script hide physics__d_309, script hide physics__lc_310, script hide physics__d_313, script hide physics__lc_314, script hide physics__d_317, script hide physics__lc_318, script hide physics__d_321, script hide physics__lc_322, script hide physics__d_325, script hide physics__lc_326, script hide physics__d_329, script hide physics__lc_330, script hide physics__d_333, script hide physics__lc_334, script hide physics__d_337, script hide physics__lc_338, script hide conn__lc_404, script hide conn__te_405, script hide conn__lc_408, script hide conn__te_409, script hide conn__b_412, script hide conn__lc_414, script hide conn__tog_415, script hide conn__lc_418, script hide conn__lc_419",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-426",
          "maxclass": "message",
          "patching_rect": [
            1840.0,
            130.0,
            200.0,
            22.0
          ],
          "text": "script show physics__d_301, script show physics__lc_302, script show physics__d_305, script show physics__lc_306, script show physics__d_309, script show physics__lc_310, script show physics__d_313, script show physics__lc_314, script show physics__d_317, script show physics__lc_318, script show physics__d_321, script show physics__lc_322, script show physics__d_325, script show physics__lc_326, script show physics__d_329, script show physics__lc_330, script show physics__d_333, script show physics__lc_334, script show physics__d_337, script show physics__lc_338, script hide midi1__t_11, script hide midi1__lc_12, script hide midi1__t_17, script hide midi1__lc_18, script hide midi1__t_23, script hide midi1__lc_24, script hide midi1__t_29, script hide midi1__lc_30, script hide midi1__t_35, script hide midi1__lc_36, script hide midi1__t_41, script hide midi1__lc_42, script hide midi1__t_47, script hide midi1__lc_48, script hide midi1__t_53, script hide midi1__lc_54, script hide midi1__t_59, script hide midi1__lc_60, script hide midi1__t_65, script hide midi1__lc_66, script hide midi1__t_71, script hide midi1__lc_72, script hide midi1__t_77, script hide midi1__lc_78, script hide midi1__t_83, script hide midi1__lc_84, script hide midi1__t_89, script hide midi1__lc_90, script hide midi1__t_95, script hide midi1__lc_96, script hide midi1__t_101, script hide midi1__lc_102, script hide midi1__t_107, script hide midi1__lc_108, script hide midi2__t_113, script hide midi2__lc_114, script hide midi2__t_119, script hide midi2__lc_120, script hide midi2__t_125, script hide midi2__lc_126, script hide midi2__t_131, script hide midi2__lc_132, script hide midi2__t_137, script hide midi2__lc_138, script hide midi2__t_143, script hide midi2__lc_144, script hide midi2__t_149, script hide midi2__lc_150, script hide midi2__t_155, script hide midi2__lc_156, script hide midi2__t_161, script hide midi2__lc_162, script hide midi2__t_167, script hide midi2__lc_168, script hide midi2__t_173, script hide midi2__lc_174, script hide midi2__t_179, script hide midi2__lc_180, script hide midi2__t_185, script hide midi2__lc_186, script hide midi2__t_191, script hide midi2__lc_192, script hide midi2__t_197, script hide midi2__lc_198, script hide midi2__t_203, script hide midi2__lc_204, script hide midi2__t_209, script hide midi2__lc_210, script hide midi2__t_215, script hide midi2__lc_216, script hide midi2__t_221, script hide midi2__lc_222, script hide midi2__t_227, script hide midi2__lc_228, script hide midi2__t_233, script hide midi2__lc_234, script hide midi2__t_239, script hide midi2__lc_240, script hide midi2__t_245, script hide midi2__lc_246, script hide midi2__t_251, script hide midi2__lc_252, script hide master__d_257, script hide master__lc_258, script hide master__d_261, script hide master__lc_262, script hide master__d_265, script hide master__lc_266, script hide master__d_269, script hide master__lc_270, script hide master__d_273, script hide master__lc_274, script hide master__d_277, script hide master__lc_278, script hide master__d_281, script hide master__lc_282, script hide master__d_285, script hide master__lc_286, script hide master__d_289, script hide master__lc_290, script hide master__d_293, script hide master__lc_294, script hide master__d_297, script hide master__lc_298, script hide rings__lc_341, script hide rings__lc_342, script hide rings__lc_343, script hide rings__lc_344, script hide rings__lc_345, script hide rings__lc_346, script hide rings__lc_347, script hide rings__d_348, script hide rings__d_351, script hide rings__d_354, script hide rings__d_357, script hide rings__d_360, script hide rings__d_363, script hide rings__lc_366, script hide rings__d_367, script hide rings__d_370, script hide rings__d_373, script hide rings__d_376, script hide rings__d_379, script hide rings__d_382, script hide rings__lc_385, script hide rings__d_386, script hide rings__d_389, script hide rings__d_392, script hide rings__d_395, script hide rings__d_398, script hide rings__d_401, script hide conn__lc_404, script hide conn__te_405, script hide conn__lc_408, script hide conn__te_409, script hide conn__b_412, script hide conn__lc_414, script hide conn__tog_415, script hide conn__lc_418, script hide conn__lc_419",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "m-427",
          "maxclass": "message",
          "patching_rect": [
            2050.0,
            130.0,
            200.0,
            22.0
          ],
          "text": "script show conn__lc_404, script show conn__te_405, script show conn__lc_408, script show conn__te_409, script show conn__b_412, script show conn__lc_414, script show conn__tog_415, script show conn__lc_418, script show conn__lc_419, script hide midi1__t_11, script hide midi1__lc_12, script hide midi1__t_17, script hide midi1__lc_18, script hide midi1__t_23, script hide midi1__lc_24, script hide midi1__t_29, script hide midi1__lc_30, script hide midi1__t_35, script hide midi1__lc_36, script hide midi1__t_41, script hide midi1__lc_42, script hide midi1__t_47, script hide midi1__lc_48, script hide midi1__t_53, script hide midi1__lc_54, script hide midi1__t_59, script hide midi1__lc_60, script hide midi1__t_65, script hide midi1__lc_66, script hide midi1__t_71, script hide midi1__lc_72, script hide midi1__t_77, script hide midi1__lc_78, script hide midi1__t_83, script hide midi1__lc_84, script hide midi1__t_89, script hide midi1__lc_90, script hide midi1__t_95, script hide midi1__lc_96, script hide midi1__t_101, script hide midi1__lc_102, script hide midi1__t_107, script hide midi1__lc_108, script hide midi2__t_113, script hide midi2__lc_114, script hide midi2__t_119, script hide midi2__lc_120, script hide midi2__t_125, script hide midi2__lc_126, script hide midi2__t_131, script hide midi2__lc_132, script hide midi2__t_137, script hide midi2__lc_138, script hide midi2__t_143, script hide midi2__lc_144, script hide midi2__t_149, script hide midi2__lc_150, script hide midi2__t_155, script hide midi2__lc_156, script hide midi2__t_161, script hide midi2__lc_162, script hide midi2__t_167, script hide midi2__lc_168, script hide midi2__t_173, script hide midi2__lc_174, script hide midi2__t_179, script hide midi2__lc_180, script hide midi2__t_185, script hide midi2__lc_186, script hide midi2__t_191, script hide midi2__lc_192, script hide midi2__t_197, script hide midi2__lc_198, script hide midi2__t_203, script hide midi2__lc_204, script hide midi2__t_209, script hide midi2__lc_210, script hide midi2__t_215, script hide midi2__lc_216, script hide midi2__t_221, script hide midi2__lc_222, script hide midi2__t_227, script hide midi2__lc_228, script hide midi2__t_233, script hide midi2__lc_234, script hide midi2__t_239, script hide midi2__lc_240, script hide midi2__t_245, script hide midi2__lc_246, script hide midi2__t_251, script hide midi2__lc_252, script hide master__d_257, script hide master__lc_258, script hide master__d_261, script hide master__lc_262, script hide master__d_265, script hide master__lc_266, script hide master__d_269, script hide master__lc_270, script hide master__d_273, script hide master__lc_274, script hide master__d_277, script hide master__lc_278, script hide master__d_281, script hide master__lc_282, script hide master__d_285, script hide master__lc_286, script hide master__d_289, script hide master__lc_290, script hide master__d_293, script hide master__lc_294, script hide master__d_297, script hide master__lc_298, script hide rings__lc_341, script hide rings__lc_342, script hide rings__lc_343, script hide rings__lc_344, script hide rings__lc_345, script hide rings__lc_346, script hide rings__lc_347, script hide rings__d_348, script hide rings__d_351, script hide rings__d_354, script hide rings__d_357, script hide rings__d_360, script hide rings__d_363, script hide rings__lc_366, script hide rings__d_367, script hide rings__d_370, script hide rings__d_373, script hide rings__d_376, script hide rings__d_379, script hide rings__d_382, script hide rings__lc_385, script hide rings__d_386, script hide rings__d_389, script hide rings__d_392, script hide rings__d_395, script hide rings__d_398, script hide rings__d_401, script hide physics__d_301, script hide physics__lc_302, script hide physics__d_305, script hide physics__lc_306, script hide physics__d_309, script hide physics__lc_310, script hide physics__d_313, script hide physics__lc_314, script hide physics__d_317, script hide physics__lc_318, script hide physics__d_321, script hide physics__lc_322, script hide physics__d_325, script hide physics__lc_326, script hide physics__d_329, script hide physics__lc_330, script hide physics__d_333, script hide physics__lc_334, script hide physics__d_337, script hide physics__lc_338",
          "numinlets": 2,
          "numoutlets": 1
        }
      },
      {
        "box": {
          "id": "n-428",
          "maxclass": "newobj",
          "patching_rect": [
            20.0,
            4.0,
            80.0,
            22.0
          ],
          "text": "live.thisdevice",
          "numinlets": 1,
          "numoutlets": 3
        }
      },
      {
        "box": {
          "id": "m-429",
          "maxclass": "message",
          "patching_rect": [
            110.0,
            4.0,
            60.0,
            22.0
          ],
          "text": "reset",
          "numinlets": 2,
          "numoutlets": 1
        }
      }
    ],
    "lines": [
      {
        "patchline": {
          "destination": [
            "n-3",
            0
          ],
          "source": [
            "n-2",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-4",
            0
          ],
          "source": [
            "n-2",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-6",
            0
          ],
          "source": [
            "n-3",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-6",
            1
          ],
          "source": [
            "n-3",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-7",
            0
          ],
          "source": [
            "n-6",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-7",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-8",
            0
          ],
          "source": [
            "n-5",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-10",
            0
          ],
          "source": [
            "n-9",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-10",
            1
          ],
          "source": [
            "n-9",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-4",
            0
          ],
          "source": [
            "n-10",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-13",
            0
          ],
          "source": [
            "t-11",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-14",
            0
          ],
          "source": [
            "n-13",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-14",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-15",
            0
          ],
          "source": [
            "n-13",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-15",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-16",
            0
          ],
          "source": [
            "n-13",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-16",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-19",
            0
          ],
          "source": [
            "t-17",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-20",
            0
          ],
          "source": [
            "n-19",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-20",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-21",
            0
          ],
          "source": [
            "n-19",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-21",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-22",
            0
          ],
          "source": [
            "n-19",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-22",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-25",
            0
          ],
          "source": [
            "t-23",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-26",
            0
          ],
          "source": [
            "n-25",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-26",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-27",
            0
          ],
          "source": [
            "n-25",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-27",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-28",
            0
          ],
          "source": [
            "n-25",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-28",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-31",
            0
          ],
          "source": [
            "t-29",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-32",
            0
          ],
          "source": [
            "n-31",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-32",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-33",
            0
          ],
          "source": [
            "n-31",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-33",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-34",
            0
          ],
          "source": [
            "n-31",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-34",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-37",
            0
          ],
          "source": [
            "t-35",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-38",
            0
          ],
          "source": [
            "n-37",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-38",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-39",
            0
          ],
          "source": [
            "n-37",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-39",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-40",
            0
          ],
          "source": [
            "n-37",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-40",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-43",
            0
          ],
          "source": [
            "t-41",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-44",
            0
          ],
          "source": [
            "n-43",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-44",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-45",
            0
          ],
          "source": [
            "n-43",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-45",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-46",
            0
          ],
          "source": [
            "n-43",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-46",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-49",
            0
          ],
          "source": [
            "t-47",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-50",
            0
          ],
          "source": [
            "n-49",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-50",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-51",
            0
          ],
          "source": [
            "n-49",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-51",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-52",
            0
          ],
          "source": [
            "n-49",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-52",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-55",
            0
          ],
          "source": [
            "t-53",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-56",
            0
          ],
          "source": [
            "n-55",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-56",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-57",
            0
          ],
          "source": [
            "n-55",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-57",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-58",
            0
          ],
          "source": [
            "n-55",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-58",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-61",
            0
          ],
          "source": [
            "t-59",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-62",
            0
          ],
          "source": [
            "n-61",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-62",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-63",
            0
          ],
          "source": [
            "n-61",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-63",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-64",
            0
          ],
          "source": [
            "n-61",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-64",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-67",
            0
          ],
          "source": [
            "t-65",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-68",
            0
          ],
          "source": [
            "n-67",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-68",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-69",
            0
          ],
          "source": [
            "n-67",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-69",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-70",
            0
          ],
          "source": [
            "n-67",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-70",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-73",
            0
          ],
          "source": [
            "t-71",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-74",
            0
          ],
          "source": [
            "n-73",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-74",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-75",
            0
          ],
          "source": [
            "n-73",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-75",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-76",
            0
          ],
          "source": [
            "n-73",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-76",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-79",
            0
          ],
          "source": [
            "t-77",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-80",
            0
          ],
          "source": [
            "n-79",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-80",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-81",
            0
          ],
          "source": [
            "n-79",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-81",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-82",
            0
          ],
          "source": [
            "n-79",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-82",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-85",
            0
          ],
          "source": [
            "t-83",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-86",
            0
          ],
          "source": [
            "n-85",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-86",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-87",
            0
          ],
          "source": [
            "n-85",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-87",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-88",
            0
          ],
          "source": [
            "n-85",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-88",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-91",
            0
          ],
          "source": [
            "t-89",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-92",
            0
          ],
          "source": [
            "n-91",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-92",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-93",
            0
          ],
          "source": [
            "n-91",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-93",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-94",
            0
          ],
          "source": [
            "n-91",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-94",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-97",
            0
          ],
          "source": [
            "t-95",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-98",
            0
          ],
          "source": [
            "n-97",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-98",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-99",
            0
          ],
          "source": [
            "n-97",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-99",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-100",
            0
          ],
          "source": [
            "n-97",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-100",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-103",
            0
          ],
          "source": [
            "t-101",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-104",
            0
          ],
          "source": [
            "n-103",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-104",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-105",
            0
          ],
          "source": [
            "n-103",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-105",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-106",
            0
          ],
          "source": [
            "n-103",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-106",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-109",
            0
          ],
          "source": [
            "t-107",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-110",
            0
          ],
          "source": [
            "n-109",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-110",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-111",
            0
          ],
          "source": [
            "n-109",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-111",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-112",
            0
          ],
          "source": [
            "n-109",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-112",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-115",
            0
          ],
          "source": [
            "t-113",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-116",
            0
          ],
          "source": [
            "n-115",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-116",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-117",
            0
          ],
          "source": [
            "n-115",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-117",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-118",
            0
          ],
          "source": [
            "n-115",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-118",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-121",
            0
          ],
          "source": [
            "t-119",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-122",
            0
          ],
          "source": [
            "n-121",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-122",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-123",
            0
          ],
          "source": [
            "n-121",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-123",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-124",
            0
          ],
          "source": [
            "n-121",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-124",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-127",
            0
          ],
          "source": [
            "t-125",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-128",
            0
          ],
          "source": [
            "n-127",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-128",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-129",
            0
          ],
          "source": [
            "n-127",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-129",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-130",
            0
          ],
          "source": [
            "n-127",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-130",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-133",
            0
          ],
          "source": [
            "t-131",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-134",
            0
          ],
          "source": [
            "n-133",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-134",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-135",
            0
          ],
          "source": [
            "n-133",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-135",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-136",
            0
          ],
          "source": [
            "n-133",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-136",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-139",
            0
          ],
          "source": [
            "t-137",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-140",
            0
          ],
          "source": [
            "n-139",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-140",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-141",
            0
          ],
          "source": [
            "n-139",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-141",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-142",
            0
          ],
          "source": [
            "n-139",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-142",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-145",
            0
          ],
          "source": [
            "t-143",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-146",
            0
          ],
          "source": [
            "n-145",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-146",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-147",
            0
          ],
          "source": [
            "n-145",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-147",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-148",
            0
          ],
          "source": [
            "n-145",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-148",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-151",
            0
          ],
          "source": [
            "t-149",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-152",
            0
          ],
          "source": [
            "n-151",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-152",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-153",
            0
          ],
          "source": [
            "n-151",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-153",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-154",
            0
          ],
          "source": [
            "n-151",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-154",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-157",
            0
          ],
          "source": [
            "t-155",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-158",
            0
          ],
          "source": [
            "n-157",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-158",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-159",
            0
          ],
          "source": [
            "n-157",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-159",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-160",
            0
          ],
          "source": [
            "n-157",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-160",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-163",
            0
          ],
          "source": [
            "t-161",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-164",
            0
          ],
          "source": [
            "n-163",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-164",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-165",
            0
          ],
          "source": [
            "n-163",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-165",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-166",
            0
          ],
          "source": [
            "n-163",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-166",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-169",
            0
          ],
          "source": [
            "t-167",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-170",
            0
          ],
          "source": [
            "n-169",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-170",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-171",
            0
          ],
          "source": [
            "n-169",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-171",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-172",
            0
          ],
          "source": [
            "n-169",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-172",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-175",
            0
          ],
          "source": [
            "t-173",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-176",
            0
          ],
          "source": [
            "n-175",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-176",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-177",
            0
          ],
          "source": [
            "n-175",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-177",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-178",
            0
          ],
          "source": [
            "n-175",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-178",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-181",
            0
          ],
          "source": [
            "t-179",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-182",
            0
          ],
          "source": [
            "n-181",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-182",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-183",
            0
          ],
          "source": [
            "n-181",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-183",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-184",
            0
          ],
          "source": [
            "n-181",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-184",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-187",
            0
          ],
          "source": [
            "t-185",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-188",
            0
          ],
          "source": [
            "n-187",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-188",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-189",
            0
          ],
          "source": [
            "n-187",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-189",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-190",
            0
          ],
          "source": [
            "n-187",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-190",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-193",
            0
          ],
          "source": [
            "t-191",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-194",
            0
          ],
          "source": [
            "n-193",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-194",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-195",
            0
          ],
          "source": [
            "n-193",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-195",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-196",
            0
          ],
          "source": [
            "n-193",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-196",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-199",
            0
          ],
          "source": [
            "t-197",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-200",
            0
          ],
          "source": [
            "n-199",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-200",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-201",
            0
          ],
          "source": [
            "n-199",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-201",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-202",
            0
          ],
          "source": [
            "n-199",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-202",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-205",
            0
          ],
          "source": [
            "t-203",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-206",
            0
          ],
          "source": [
            "n-205",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-206",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-207",
            0
          ],
          "source": [
            "n-205",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-207",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-208",
            0
          ],
          "source": [
            "n-205",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-208",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-211",
            0
          ],
          "source": [
            "t-209",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-212",
            0
          ],
          "source": [
            "n-211",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-212",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-213",
            0
          ],
          "source": [
            "n-211",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-213",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-214",
            0
          ],
          "source": [
            "n-211",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-214",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-217",
            0
          ],
          "source": [
            "t-215",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-218",
            0
          ],
          "source": [
            "n-217",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-218",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-219",
            0
          ],
          "source": [
            "n-217",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-219",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-220",
            0
          ],
          "source": [
            "n-217",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-220",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-223",
            0
          ],
          "source": [
            "t-221",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-224",
            0
          ],
          "source": [
            "n-223",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-224",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-225",
            0
          ],
          "source": [
            "n-223",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-225",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-226",
            0
          ],
          "source": [
            "n-223",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-226",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-229",
            0
          ],
          "source": [
            "t-227",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-230",
            0
          ],
          "source": [
            "n-229",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-230",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-231",
            0
          ],
          "source": [
            "n-229",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-231",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-232",
            0
          ],
          "source": [
            "n-229",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-232",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-235",
            0
          ],
          "source": [
            "t-233",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-236",
            0
          ],
          "source": [
            "n-235",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-236",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-237",
            0
          ],
          "source": [
            "n-235",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-237",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-238",
            0
          ],
          "source": [
            "n-235",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-238",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-241",
            0
          ],
          "source": [
            "t-239",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-242",
            0
          ],
          "source": [
            "n-241",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-242",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-243",
            0
          ],
          "source": [
            "n-241",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-243",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-244",
            0
          ],
          "source": [
            "n-241",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-244",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-247",
            0
          ],
          "source": [
            "t-245",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-248",
            0
          ],
          "source": [
            "n-247",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-248",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-249",
            0
          ],
          "source": [
            "n-247",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-249",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-250",
            0
          ],
          "source": [
            "n-247",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-250",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-253",
            0
          ],
          "source": [
            "t-251",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-254",
            0
          ],
          "source": [
            "n-253",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-254",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-255",
            0
          ],
          "source": [
            "n-253",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-255",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-256",
            0
          ],
          "source": [
            "n-253",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-9",
            0
          ],
          "source": [
            "m-256",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-259",
            0
          ],
          "source": [
            "d-257",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-260",
            0
          ],
          "source": [
            "n-259",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-260",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-263",
            0
          ],
          "source": [
            "d-261",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-264",
            0
          ],
          "source": [
            "n-263",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-264",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-267",
            0
          ],
          "source": [
            "d-265",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-268",
            0
          ],
          "source": [
            "n-267",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-268",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-271",
            0
          ],
          "source": [
            "d-269",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-272",
            0
          ],
          "source": [
            "n-271",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-272",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-275",
            0
          ],
          "source": [
            "d-273",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-276",
            0
          ],
          "source": [
            "n-275",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-276",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-279",
            0
          ],
          "source": [
            "d-277",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-280",
            0
          ],
          "source": [
            "n-279",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-280",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-283",
            0
          ],
          "source": [
            "d-281",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-284",
            0
          ],
          "source": [
            "n-283",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-284",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-287",
            0
          ],
          "source": [
            "d-285",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-288",
            0
          ],
          "source": [
            "n-287",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-288",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-291",
            0
          ],
          "source": [
            "d-289",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-292",
            0
          ],
          "source": [
            "n-291",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-292",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-295",
            0
          ],
          "source": [
            "d-293",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-296",
            0
          ],
          "source": [
            "n-295",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-296",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-299",
            0
          ],
          "source": [
            "d-297",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-300",
            0
          ],
          "source": [
            "n-299",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-300",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-303",
            0
          ],
          "source": [
            "d-301",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-304",
            0
          ],
          "source": [
            "n-303",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-304",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-307",
            0
          ],
          "source": [
            "d-305",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-308",
            0
          ],
          "source": [
            "n-307",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-308",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-311",
            0
          ],
          "source": [
            "d-309",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-312",
            0
          ],
          "source": [
            "n-311",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-312",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-315",
            0
          ],
          "source": [
            "d-313",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-316",
            0
          ],
          "source": [
            "n-315",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-316",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-319",
            0
          ],
          "source": [
            "d-317",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-320",
            0
          ],
          "source": [
            "n-319",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-320",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-323",
            0
          ],
          "source": [
            "d-321",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-324",
            0
          ],
          "source": [
            "n-323",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-324",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-327",
            0
          ],
          "source": [
            "d-325",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-328",
            0
          ],
          "source": [
            "n-327",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-328",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-331",
            0
          ],
          "source": [
            "d-329",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-332",
            0
          ],
          "source": [
            "n-331",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-332",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-335",
            0
          ],
          "source": [
            "d-333",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-336",
            0
          ],
          "source": [
            "n-335",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-336",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-339",
            0
          ],
          "source": [
            "d-337",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-340",
            0
          ],
          "source": [
            "n-339",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-340",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-349",
            0
          ],
          "source": [
            "d-348",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-350",
            0
          ],
          "source": [
            "n-349",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-350",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-352",
            0
          ],
          "source": [
            "d-351",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-353",
            0
          ],
          "source": [
            "n-352",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-353",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-355",
            0
          ],
          "source": [
            "d-354",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-356",
            0
          ],
          "source": [
            "n-355",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-356",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-358",
            0
          ],
          "source": [
            "d-357",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-359",
            0
          ],
          "source": [
            "n-358",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-359",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-361",
            0
          ],
          "source": [
            "d-360",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-362",
            0
          ],
          "source": [
            "n-361",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-362",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-364",
            0
          ],
          "source": [
            "d-363",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-365",
            0
          ],
          "source": [
            "n-364",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-365",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-368",
            0
          ],
          "source": [
            "d-367",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-369",
            0
          ],
          "source": [
            "n-368",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-369",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-371",
            0
          ],
          "source": [
            "d-370",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-372",
            0
          ],
          "source": [
            "n-371",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-372",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-374",
            0
          ],
          "source": [
            "d-373",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-375",
            0
          ],
          "source": [
            "n-374",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-375",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-377",
            0
          ],
          "source": [
            "d-376",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-378",
            0
          ],
          "source": [
            "n-377",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-378",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-380",
            0
          ],
          "source": [
            "d-379",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-381",
            0
          ],
          "source": [
            "n-380",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-381",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-383",
            0
          ],
          "source": [
            "d-382",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-384",
            0
          ],
          "source": [
            "n-383",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-384",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-387",
            0
          ],
          "source": [
            "d-386",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-388",
            0
          ],
          "source": [
            "n-387",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-388",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-390",
            0
          ],
          "source": [
            "d-389",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-391",
            0
          ],
          "source": [
            "n-390",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-391",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-393",
            0
          ],
          "source": [
            "d-392",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-394",
            0
          ],
          "source": [
            "n-393",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-394",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-396",
            0
          ],
          "source": [
            "d-395",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-397",
            0
          ],
          "source": [
            "n-396",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-397",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-399",
            0
          ],
          "source": [
            "d-398",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-400",
            0
          ],
          "source": [
            "n-399",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-400",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-402",
            0
          ],
          "source": [
            "d-401",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-403",
            0
          ],
          "source": [
            "n-402",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "n-403",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-406",
            0
          ],
          "source": [
            "te-405",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-407",
            0
          ],
          "source": [
            "n-406",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-8",
            0
          ],
          "source": [
            "n-407",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-410",
            0
          ],
          "source": [
            "te-409",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-411",
            0
          ],
          "source": [
            "n-410",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-8",
            0
          ],
          "source": [
            "n-411",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-413",
            0
          ],
          "source": [
            "b-412",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-413",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-416",
            0
          ],
          "source": [
            "tog-415",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-416",
            1
          ],
          "source": [
            "n-5",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-417",
            0
          ],
          "source": [
            "n-416",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-421",
            0
          ],
          "source": [
            "tab-1",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-422",
            0
          ],
          "source": [
            "n-421",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-420",
            0
          ],
          "source": [
            "m-422",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-423",
            0
          ],
          "source": [
            "n-421",
            1
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-420",
            0
          ],
          "source": [
            "m-423",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-424",
            0
          ],
          "source": [
            "n-421",
            2
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-420",
            0
          ],
          "source": [
            "m-424",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-425",
            0
          ],
          "source": [
            "n-421",
            3
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-420",
            0
          ],
          "source": [
            "m-425",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-426",
            0
          ],
          "source": [
            "n-421",
            4
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-420",
            0
          ],
          "source": [
            "m-426",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-427",
            0
          ],
          "source": [
            "n-421",
            5
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-420",
            0
          ],
          "source": [
            "m-427",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-429",
            0
          ],
          "source": [
            "n-428",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "n-5",
            0
          ],
          "source": [
            "m-429",
            0
          ]
        }
      },
      {
        "patchline": {
          "destination": [
            "m-422",
            0
          ],
          "source": [
            "n-428",
            0
          ]
        }
      }
    ]
  }
}
