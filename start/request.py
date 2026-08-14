
from urllib import request


def getGames():
        url = "https://api-v2.sportsdynamics.eu/graphql"
        query = """
        query getGames($filters: [GameFilter!], $pagination: PaginationInput, $sort: [GameSortPaginationInput!]) {
            getGames(filters: $filters, pagination: $pagination, sort: $sort) {
                items {
                    id
                    name
                    result
                    startsAt
                    playedAt
                    round {
                        name
                    }
                    homeScore
                    awayScore
                    homeTeamFormation
                    awayTeamFormation
                    homeTeam {
                        brand
                        id
                    }
                    awayTeam {
                        brand
                        id
                    }
                    gameOutputFiles {
                        items {
                            id
                            name
                            fileName
                            isOutdated
                            version
                            createdAt
                            updatedAt
                            expiresAt
                            fileType
                            file {
                                name
                                meta
                                size
                                url
                                lastModifiedAt
                                mimeType
                            }
                        }
                    }

                    periods {
                        id
                        periodId
                        periodStartTime
                        periodEndTime
                        relativeStartTime
                        relativeEndTime
                        overTimeDuration
                    }

                    squads {
                        teamId
                        players: {
                            meta
                            items {
                                id
                                isStarting
                                isCaptain
                                formationField
                                formationPosition
                                jerseyNumber
                                playingTime
                                player {
                                    id
                                    firstName
                                    lastName
                                    name
                                    usageName
                                }
                            }
                        }
                    } 

                    providers {
	                    items {
                            id
                            externalId
                            provider {
                                id
                                name
                            }
	                }


                }
            }
        }
        """
        filters = [{"available": {"equals": True}}]
        filters[0]['season'] = {"season": {"equals": self.Setting.config_SportsDynamics.season}}
        filters[0]["round"] = {"name": {"in": [str(gw) for gw in self.Setting.config_SportsDynamics.gameDay]}}
        filters[0]["competition"] = {"id": {"equals": self.Setting.config_SportsDynamics.id_championship}}
        variables = {
            "filters": filters,
            "pagination": {"limit": 380, "page": 1},
        }

        r = requests.post(url, json={"query": query, "variables": variables}, headers=self.Setting.config_SportsDynamics.header)

def getCompetitions(): 
    url = "https://api-v2.sportsdynamics.eu/graphql"
    query = """
        query getCompetitions(
            $filters: [CompetitionFilter!]
            $pagination: PaginationInput
            $sort: [CompetitionSortPaginationInput!]
            ) {
            getCompetitions(filters: $filters, pagination: $pagination, sort: $sort) {
                meta {
                count
                pageCount
                currentPage
                }
                items {
                id
                name
                seasons {
                    items {
                        id
                        name
                        season
                        }  
                }
                }
            }
            }
        """

def getSeason(): 
    url = "https://api-v2.sportsdynamics.eu/graphql"
    query = """
        query getSeasons(
        $filters: [SeasonFilter!]
        $pagination: PaginationInput
        $sort: [SeasonSortPaginationInput!]
        ) {
        getSeasons(filters: $filters, pagination: $pagination, sort: $sort) {
            meta {
            count
            pageCount
            currentPage
            }
            items {
            id
            name
            season
            stages {
                items {
                    id
                    name
                    type
                    }  
            }
            }
        }
        }

    """ 

def getClubs(): 
    url = "https://api-v2.sportsdynamics.eu/graphql"
    query = """
        query getClubs(
        $filters: [ClubFilter!]
        $pagination: PaginationInput
        $sort: [SeasonSortPaginationInput!]
        ) {
        getClubs(filters: $filters, pagination: $pagination, sort: $sort) {
            meta {
            count
            pageCount
            currentPage
            }
            items {
            id
            brand
            logoUrl
            games { items { id name } } // report on game object
            providers { items { externalId provider { name } } // same as game provider object
            }
        }
        }

    """

def getProvider(): 
    url = "https://api-v2.sportsdynamics.eu/graphql"
    query = """
        query getProviders(
        $filters: [ProviderFilter!]
        $pagination: PaginationInput
        $sort: [ProviderSortPaginationInput!]
        ) {
        getProviders(filters: $filters, pagination: $pagination, sort: $sort) {
            meta {
            count
            pageCount
            currentPage
            }
            items {
            id
            name
            }
        }
        }
    """


def getFormation(): 
    url = "https://api-v2.sportsdynamics.eu/graphql"
    query = """
        query getFormationById {
        getFormationById(id: "4-4-2") {
            id
            lines {
            id
            group
            positions {
                code
                formationField
            }
            }
        }
        }
    """


def getPlayer(): 
    url = "https://api-v2.sportsdynamics.eu/graphql"
    query = """
        query getPlayers(
        $filters: [PlayerFilter!]
        $pagination: PaginationInput
        $sort: [PlayerSortPaginationInput!]
        ) {
        getPlayers(filters: $filters, pagination: $pagination, sort: $sort) {
            items {
            id
            firstName
            lastName
            name
            usageName
            photo
            age
            birthdate
            currentTeam {
                id
                brand
            }
            nationalities {
                items {
                id
                country {
                    iso3
                }
                sportive
                }
            }
            currentNationalTeam {
                id
                brand
            }
            positions {
                items {
                id
                position {
                    name
                    code
                    group
                }
                }
            }
            }
        }
        }
    """


def downlaodFile(fileUrl, fileName):
    request.urlretrieve(fileUrl, fileName)
