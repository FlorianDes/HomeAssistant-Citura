import json
from datetime import datetime, timezone, date
import requests
import requests

BASE_URL = "http://catp-reims.airweb.fr/feed"


class CituraAPI:
    def __init__(self) -> None:
        pass

    def getAllLines(self):
        location = "/Line/getAllLines.json"
        response = self.sendRequest(location)
        if 'response' not in response or 'lines' not in response['response']:
            return []
        response = response['response']['lines']
        return [
            {
                'line_id': elem['line_id'],
                'name': elem['name'],
                '1': elem['direction']['aller'],
                '0': elem['direction']['retour']
            } for elem in response
        ]

    def getLine(self, line) -> dict:
        location = "/Line/getLine.json"
        params = {"line": line}
        response = self.sendRequest(location, params)
        if 'response' not in response:
            return {}
        response = response['response']
        return {'line_id': response['line_id'],
                'name': response['name'],
                '1': response['direction']['aller'],
                '0': response['direction']['retour']
                }

    def getLinesByStation(self, station):
        location = "/Line/getStationLines.json"
        params = {"station": station.upper()}
        response = self.sendRequest(location, params)
        if 'response' not in response or 'lines' not in response['response']:
            return []
        return response['response']['lines']

    def getAllStations(self):
        location = "/Station/getAllStations.json"
        response = self.sendRequest(location)
        response = response.get('response').get('stations')
        if 'response' not in response or 'stations' not in response['response']:
            return []
        return [{
            'stop_id': elem.get('stop_id'),
            'name': elem.get('name'),
            'latitude': elem.get('latitude'),
            'longitude': elem.get('longitude'),

        } for elem in response]

    def getStationId(self, station, line):
        station = station.upper()
        location = "/Station/getBoardingIDs.json"
        params = {"station": station, "line": line}
        response = self.sendRequest(location, params)
        if 'response' not in response:
            return []
        return {
            'stop_id': response['response']['stop_id'],
            '1': response['response']['boarding_ids']['aller'],
            '0': response['response']['boarding_ids']['retour']
        }

    def getNearest(self, latitude, longitude):
        location = "/Station/getNearest.json"
        params = {"latitude": latitude, "longitude": longitude}
        response = self.sendRequest(location, params)
        if not 'response' in response or not 'nearest' in response['response']:
            return {}
        response = response['response']
        return response['nearest']

    def getHoraire(self, station, line, direction=1, dateWhen=None):
        station = station.upper()
        location = "/Horaire/getHoraire.json"
        if not dateWhen:
            dateWhen = datetime.now()

        s = self.getStationId(station, line)

        params = {"date": dateWhen.isoformat(),
                  "line": line,
                  "stop_id": s[str(direction)][0] if str(direction) in s else s['stop_id'],
                  "direction": direction}

        response = self.sendRequest(location, params)
        if not 'response' in response:
            return []
        response = response['response']
        return [{'time': elem['time']} for elem in response['horaire']]

    def getStationInfo(self, station):
        location = "/Station/getStationInfo.json"
        station = station.upper()
        params = {"name": station}
        response = self.sendRequest(location, params)
        if not 'response' in response or not 'station' in response['response']:
            return {}
        response = response['response']
        return response['station']

    def getStationLocation(self, station):
        station = station.upper()
        response = self.getStationInfo(station)
        if not 'latitude' in response or not 'longitude' in response:
            return {}
        return [response['latitude'], response['longitude']]

    # def getItinariesStation(self, start_name, end_name):
    #     start = self.getStationLocation(start_name)
    #     end = self.getStationLocation(end_name)
    #     return self.getItinaries(start[0], start[1], end[0], end[1])

    def getItinaries(self, *, start_name=None, end_name=None, start_lat=None, start_lng=None, end_lat=None, end_lng=None):
        location = "/Itinerary/getItineraries.json"
        if start_name:
            start_lat, start_lng = self.getStationLocation(start_name)
        if end_name:
            end_lat, end_lng = self.getStationLocation(end_name)

        if not start_lat or not start_lng or not end_lat or not end_lng:
            return []

        params = {"start": f"[{start_lat},{start_lng}]",
                  "end": f"[{end_lat},{end_lng}]",
                  "count": 5}

        response = self.sendRequest(location, params)
        response = response['response']

        return [{
            'itinary': [{'start': elem['start'],
                         'start_time': elem['startTime'],
                         'end': elem['end'],
                         'end_time': elem['endTime'],
                         'line': elem['line']['lineName'] if elem['line'] else '',
                         'destination': elem['line']['destination'] if elem['line'] else '',
                         'type': elem['line']['type'] if elem['line'] else '',
                         'instruction': elem['instruction'],
                         'distance': elem['travelDistance'],
                         'time': elem['travelTime'],
                         'infos': elem['line']['trafficInfos'] if elem['line'] else []
                         }
                        for elem in travel['itinerary']],
                'time': travel['totalTravelTime'],
                'connections': travel['connections']} for travel in response]

    def getFuzzy(self, name) -> list:
        location = "/Station/remindStations.json"
        params = {"prefix": name}
        response = self.sendRequest(location, params)
        if 'response' not in response or 'names' not in response['response']:
            return []
        response = response['response']
        return response['names']

    def getSIRI(self, line, *, stop_name=None, stop_point=None, count=None, sens=None):
        location = "/SIRI/getSIRIWithErrors.json"
        if not (stop_name and sens) and not stop_point:
            raise ValueError("stop_name and sens or stop_point should be set")
        params = {"stopPoint": stop_point}
        if stop_name:
            idx = self.getStationId(stop_name, line)
            if sens:
                params["stopPoint"] = idx[str(sens)][0]
            else:
                params["stopPoint"] = idx['stop_id'][0]
        if count:
            params['max'] = count
        if line:
            params['line'] = line
        response = self.sendRequest(location, params)
        if not 'response' in response:
            return {'time': [{
                "expected_time": None,
                "aimed_time": None,
                "line": line,
                "destination": None,
                "status": None,
                "realtime": None
            }],
                'empty': None,
                'error': None}
        response = response['response']
        return {'time': [{
            "expected_time": datetime.fromisoformat(elem['expectedDepartureTime']).astimezone(timezone.utc).isoformat(),
            "aimed_time": datetime.fromisoformat(elem['aimedDepartureTime']).astimezone(timezone.utc).isoformat(),
            "line": elem['line']['line_id'],
            "destination": elem['destinationName'],
            'status': elem['departureStatus'],
            'realtime': elem['realtime']
        } for elem in response['realtime']],
            'empty': response['realtime_empty'],
            'error': response['realtime_error']}

    def sendRequest(self, location, params=None):
        try:
            response = requests.get(
                BASE_URL+location, params=params, timeout=10)
            # response = self.http.request(
            #     'GET',
            #     BASE_URL+location,
            #     fields=params,
            #     headers=headers)
            result = response.json()
        except requests.exceptions.ReadTimeout:
            return {}
        except json.decoder.JSONDecodeError:
            return {}
        if 'response' in result and 'errorMessage' in result['response']:
            return {}
        return result


if __name__ == '__main__':
    citura = CituraAPI()

    # res = citura.getAllLines()
    # res = citura.getLine("03")
    # res = citura.getAllStations()
    # res = citura.getLinesByStation("etape")
    # res = citura.getStationId("etape", "03")
    lat_start = 49.25308318540147
    lng_start = 4.025021444030424
    lat_end = 49.24311484246807
    lng_end = 4.06262266418303
    # res = citura.getNearest(lat_start, lng_start)
    # start = res['stop_id']
    # res = citura.getHoraire('etape', '03')
    # res = citura.getStationInfo('vesle')
    # res = citura.getStationLocation('moulin housse')
    # res = citura.getItinaries(start_name='etape', end_name='moulin housse')
    # res = citura.getItinaries(start_lat=lat_start, start_lng=lng_start, end_name='moulin housse')
    # res = citura.getItinaries(
    #     start_lat=lat_start, start_lng=lng_start, end_lat=lat_end, end_lng=lng_end)
    # res = citura.getItinaries(
    #     start_lat=lat_start, start_lng=lng_start, end_name='moulin housse')
    # res = citura.getFuzzy('eta')
    res = citura.getSIRI(line='03', stop_point='305', count=3)

    print(json.dumps(res, indent=2))
