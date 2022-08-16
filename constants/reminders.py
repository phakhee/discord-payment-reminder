REMINDERS = {
    "first_day": {
        "text": lambda user_id, mentions: f"Het is vandaag renewal dag, <@{user_id}>! {mentions} komt eraan en maakt direc"
                                          f"t een betaalverzoekje voor je aan. Hierdoor kunnen wij weer lekker snel doo"
                                          f"rgaan met koken! Weet wel, als het 5 dagen duurt voordat je betaald, moeten"
                                          f" wij helaas je licentie verwijderen!",
        "dm_text": lambda user_id, channel_id: f"Het is vandaag renewal dag, <@{user_id}>! Check <#{channel_id}> om te "
                                               f"betalen.",
        "day_difference": 0
    },
    "second_day": {
        "text": lambda user_id, mentions: f"Renewal dag is geweest <@{user_id}>! Betaal zo snel mogelijk het betaalverz"
                                          f"oek zodat we lekker snel door kunnen gaan met koken. Je hebt nog 3 dagen om"
                                          f" te betalen. Als het langer duurt moeten wij helaas je licentie verwijderen.",
        "dm_text": lambda user_id, channel_id: f"Renewal dag is geweest <@{user_id}>! Je hebt nog 3 dagen om te betalen"
                                               f". Check <#{channel_id}> om te betalen.",
        "day_difference": 1
    },
    "fourth_day": {
        "text": lambda user_id, mentions: f"Renewal dag is geweest <@{user_id}>! Betaal zo snel mogelijk het betaalverz"
                                          f"oek zodat we lekker snel door kunnen gaan met koken. Je hebt nog 1 dag om t"
                                          f"e betalen. Als het langer duurt moeten wij helaas je licentie verwijderen.",
        "dm_text": lambda user_id, channel_id: f"Renewal dag is geweest <@{user_id}>! Je hebt nog 1 dag om te betalen"
                                               f". Check <#{channel_id}> om te betalen.",
        "day_difference": 3
    },
    "sixth_day": {
        "text": lambda user_id, mentions: f"Helaas heb je niet betaald voor de renewal <@{user_id}>. Je licentie wordt "
                                          f"nu verwijderd. Hopelijk zien we je snel terug! Dit kanaal wordt na een dag"
                                          f" verwijderd.",
        "dm_text": lambda user_id, channel_id: f"Helaas heb je niet betaald voor de renewal <@{user_id}>. Je licentie w"
                                               f"ordt nu verwijderd. Hopelijk zien we je snel terug!",
        "day_difference": 5
    }
}
