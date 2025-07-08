def calc_kda(kills, deaths, assists):
    return (kills + assists) / deaths if deaths != 0 else (kills + assists)