defmodule Constants do
  @known_locales [
    "ar_AR",
    "de_DE",
    "en_GB",
    "es_ES",
    "fa_IR",
    "fil_PH",
    "fr_FR",
    "hu_HU",
    "it_IT",
    "ja_JA",
    "kw_KW",
    "nl_NL",
    "pl_PL",
    "pt_BR",
    "pt_PT",
    "ru_RU",
    "sv_SE",
    "tr_TR",
    "zh_CN",
    "zh_TW",
    "ko_KR"
  ]

  @role_ids [
    "acrobat",
    "alchemist",
    "alhadikhia",
    "amnesiac",
    "angel",
    "apprentice",
    "artist",
    "assassin",
    "atheist",
    "balloonist",
    "barber",
    "barista",
    "baron",
    "beggar",
    "bishop",
    "boffin",
    "bonecollector",
    "boomdandy",
    "bountyhunter",
    "buddhist",
    "bureaucrat",
    "butcher",
    "butler",
    "cannibal",
    "cerenovus",
    "chambermaid",
    "chef",
    "choirboy",
    "clockmaker",
    "courtier",
    "cultleader",
    "damsel",
    "deusexfiasco",
    "deviant",
    "devilsadvocate",
    "djinn",
    "doomsayer",
    "dreamer",
    "drunk",
    "duchess",
    "empath",
    "engineer",
    "eviltwin",
    "exorcist",
    "fanggu",
    "farmer",
    "fearmonger",
    "fibbin",
    "fiddler",
    "fisherman",
    "flowergirl",
    "fool",
    "fortuneteller",
    "gambler",
    "gangster",
    "general",
    "goblin",
    "godfather",
    "golem",
    "goon",
    "gossip",
    "grandmother",
    "gunslinger",
    "harlot",
    "hellslibrarian",
    "heretic",
    "huntsman",
    "imp",
    "innkeeper",
    "investigator",
    "judge",
    "juggler",
    "king",
    "klutz",
    "legion",
    "leviathan",
    "librarian",
    "lilmonsta",
    "lleech",
    "lordoftyphon",
    "lunatic",
    "lycanthrope",
    "magician",
    "marionette",
    "mastermind",
    "mathematician",
    "matron",
    "mayor",
    "mezepheles",
    "minstrel",
    "monk",
    "moonchild",
    "mutant",
    "nightwatchman",
    "noble",
    "nodashii",
    "oracle",
    "pacifist",
    "philosopher",
    "pithag",
    "pixie",
    "po",
    "poisoner",
    "politician",
    "poppygrower",
    "preacher",
    "professor",
    "psychopath",
    "pukka",
    "puzzlemaster",
    "ravenkeeper",
    "recluse",
    "revolutionary",
    "riot",
    "sage",
    "sailor",
    "saint",
    "savant",
    "scapegoat",
    "scarletwoman",
    "seamstress",
    "sentinel",
    "shabaloth",
    "slayer",
    "snakecharmer",
    "snitch",
    "soldier",
    "spiritofivory",
    "spy",
    "stormcatcher",
    "sweetheart",
    "tealady",
    "thief",
    "tinker",
    "towncrier",
    "toymaker",
    "undertaker",
    "vigormortis",
    "virgin",
    "vortox",
    "voudon",
    "washerwoman",
    "widow",
    "witch",
    "zombuul"
  ]

  @role_ids_to_normalized %{
    "bountyhunter" => "bounty_hunter",
    "cultleader" => "cult_leader",
    "fortuneteller" => "fortune_teller",
    "poppygrower" => "poppy_grower",
    "snakecharmer" => "snake_charmer",
    "towncrier" => "town_crier",
    "tealady" => "tea_lady",
    "devilsadvocate" => "devils_advocate",
    "eviltwin" => "evil_twin",
    "pithag" => "pit-hag",
    "scarletwoman" => "scarlet_woman",
    "alhadikhia" => "al-hadikhia",
    "fanggu" => "fang_gu",
    "lilmonsta" => "lil_monsta",
    "nodashii" => "no_dashii",
    "bonecollector" => "bone_collector"
  }

  @csv_headers [
    "id",
    "name",
    "ability",
    "firstNightReminder",
    "otherNightReminder",
    "remindersGlobal",
    "reminders"
  ]

  def get_known_locales() do
    @known_locales
  end

  def get_ordered_role_ids() do
    @role_ids
  end

  def get_csv_headers do
    @csv_headers
  end

  def normalize_role_id(role_id) do
    Map.get(@role_ids_to_normalized, role_id, role_id)
  end
end
