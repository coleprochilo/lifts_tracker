# Maps primary exercise names to their aliases.
# Used to seed the exercises and exercise_aliases tables on DB init.
# All names are lowercase.

EXERCISE_MAPPING = {
    # Squat
    "squat": ["squat (b)", "heavy squat", "heavy squat (b)", "light squat", "light squat (b)"],
    "bike squats": [],
    "cossack squats": [],
    "db sumo squats": [],
    "baby leg press": [],
    "one leg baby leg press": [],

    # Bench
    "bench": ["bench (p)", "heavy bench", "heavy bench (p)", "light bench", "light bench (p)", "llight bench (p)"],

    # Rows
    "bb rows": [],
    "supinated bb rows": ["supinted bb rows"],
    "incline db rows": [],
    "one arm db rows": ["one arm dumbell rows"],
    "kneeling one arm cable rows": ["kneeling 1 arm cable rows", "one arm kneeling cable rows"],
    "seated neutral cable rows": ["neutral seated cable rows", "neutral seated cabler rows"],
    "seated pronated cable rows": [],
    "seated supinated one arm cable rows": [],
    "seated supinated cable rows": ["supinated cable rows"],
    "kneeling supinated cable rows": ["supinated kneeling cable rows"],
    "knee on bench db r delt rows": ["r delt knee on bench rows"],

    # Lat pulldowns
    "lat pulldowns": [],
    "neutral lat pulldowns": [],
    "wide grip lat pulldowns": [],
    "two grip lat pulldowns": [],
    "supinated lat pulldowns": ["supinated lat pulldows"],

    # Curls
    "bayesian curls": ["standing bayesian curls"],
    "bb curls": [],
    "db curls": [],
    "db hammer curls": ["hammer curls"],
    "incline db curls": ["incline curls", "incline bicep curls"],
    "one arm db preacher curls": ["db one arm preacher curls", "one db preacher curls"],
    "ez bar preacher curls": ["ez preacher curls"],
    "spider curls": [],
    "rope cable curls": ["rope curls"],
    "flat bar cable curls": ["straight bar cable curls"],
    "one arm cable curls": ["single arm cable curls"],

    # Triceps
    "rope triceps pushdowns": ["rope pushdowns"],
    "flat bar triceps pushdowns": ["flat bar pushdowns", "straight bar pushdowns", "straight bar cable pushdowns", "flat bar cable pushdowns"],
    "standing flat bar triceps extensions": ["standing overhead tricep cable extensions"],
    "seated flat bar triceps extensions": [],
    "v bar pushdowns": [],
    "lean back one arm cable triceps pushdowns": ["lean back cable tricep pushdowns"],
    "standing rope triceps extensions": ["rope cable tricep extensions"],
    "seated rope triceps extensions": [],
    "one arm cable pushdowns": [],
    "single arm cable triceps extensions": ["single arm cable extensions"],
    "one arm db overhead triceps extensions": ["one arm db triceps overhead extensions", "one arm db overhead extensions", "one arm overhead db extensions"],
    "db skull crushers": ["skull crushers"],
    "triceps press machine": ["tricpes press machine"],

    # Lateral raises
    "cable lateral raises": [],
    "db lateral raises": ["db laterl raises"],
    "lean in db lateral raises": ["leaning db lateral raises", "leaning db lateral flys", "leaning lateral db raises", "leaning lateral raises"],
    "lean out db lateral raises": [],
    "incline db lateral raises": ["incline leaning lateral raises", "lincline db lateral raises"],

    # Rear delts
    "db bent over r delt flys": ["bent over r delt flys", "bent over db flys"],
    "bent over cable r delt flys": ["bent over r delt cable flys", "cable r delt flys", "r delt cable flys"],
    "seated bent over r delt flys": ["seated db r delt flys"],
    "mr incredible": [],
    "reverse mr incredible": [],

    # Chest
    "incline db press": ["incline db bench"],
    "incline db flys": ["incline db fliys"],
    "flat db flys": [],
    "pec fly machine": ["chest fly machine"],
    "chest press machine": [],
    "incline smith machine press": ["smith machine incline press"],
    "standing cable chest press": [],
    "standing one arm db chest flys": ["standing single arm db fly"],
    "cable upper pec flys": ["upper pec cable flys"],
    "seated cable upper pec flys": ["seated upper pec cable flys"],

    # Shoulder press
    "standing db overhead press": ["db overhead press"],
    "seated db overhead press": ["db seated overhead press", "seated db shoulder press"],
    "upright rows": [],

    # Pullovers
    "flat bar lat pullovers": ["flat bar cable pullovers"],
    "rope lat pullovers": ["rope pullovers"],

    # RDLs
    "bb rdls": [],
    "db rdls": ["db rdls (b) (2 dbs)"],

    # Legs
    "hammy curls machine": ["hammy curls"],
    "leg extensions machine": ["leg extensions"],
    "walking db lunges": [],
    "standing db lunges": ["db lunges"],
    "db bulgarian split squats": ["bulgarian split squats (2 dbs)"],

    # Face pulls
    "bar face pulls": ["face pulls"],
    "rope face pulls": [],

    # Misc
    "db kickbacks": [],
    "hip adduction machine": ["sus machine in"],
}
