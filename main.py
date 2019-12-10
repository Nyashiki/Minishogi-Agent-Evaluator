import datetime
import minishogilib
import queue
import simplejson as json
import subprocess
import threading
import time

class Engine():
    def __init__(self, name=None, path=None, cwd=None, args={}, usi_option={}):
        self.name = name
        self.usi_option = usi_option

        command = path
        for (key, value) in args.items():
            command = '{} {} {}'.format(command, key, value)

        self.process = subprocess.Popen(command.split(), cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.message_queue = queue.Queue()
        threading.Thread(target=self._message_reader).start()

    def _message_reader(self, verbose=False):
        """Receive message from the engine through standard output and store it.
        # Arguments
            verbose: If true, print message in stdout.
        """
        with self.process.stdout:
            for line in iter(self.process.stdout.readline, b''):
                message = line.decode('utf-8').rstrip('\r\n')
                self.message_queue.put(message)

                if verbose:
                    print('<:', message)

    def send_message(self, message, verbose=False):
        """Send message to the engine through standard input.
        # Arguments
            message: message sent to the engine.
            verbose: If true, print message in stdout.
        """
        if verbose:
            print('>:', message)

        message = (message + '\n').encode('utf-8')
        self.process.stdin.write(message)
        self.process.stdin.flush()

    def readline(self):
        message = self.message_queue.get()
        return message

    def ask_nextmove(self, position, timelimits, byoyomi):
        sfen_position = 'position sfen ' + position.sfen(True)
        command = 'go btime {} wtime {} byoyomi {}'.format(timelimits[0], timelimits[1], byoyomi)

        self.send_message(sfen_position)
        self.send_message(command)

        while True:
            line = self.readline().split()

            if line[0] == 'bestmove':
                return line[1]

    def usi(self):
        self.send_message('usi')

        while True:
            line = self.readline()

            if line == 'usiok':
                break

    def isready(self):
        for (key, value) in self.usi_option.items():
            command = 'setoption name {} value {}'.format(key, value)
            self.send_message(command)

        self.send_message('isready')

        while True:
            line = self.readline()

            if line == 'readyok':
                break

    def usinewgame(self):
        self.send_message('usinewgame')

    def quit(self):
        self.send_message('quit')


class GameRecord():
    def __init__(self, name1=None, name2=None):
        self.first_player = 0
        self.winner = 'DRAW'
        self.ply = 0
        self.sfen_kif = ''
        self.timestamp = 0


def conduct_game(engines, max_moves, timelimit, byoyomi):
    assert len(engines) == 2, "len(engines) should be 2."

    # Initialize engines.
    for engine in engines:
        engine.isready()
        engine.usinewgame()

    # Game record.
    game_record = GameRecord(engines[0].name, engines[1].name)
    position = minishogilib.Position()
    position.set_start_position()

    timelimits = [timelimit, timelimit]

    player_str = ['SENTE', 'GOTE']

    # Let's start a game!
    for ply in range(max_moves):
        player = ply % 2

        legal_moves = position.generate_moves()

        if len(legal_moves) == 0:
            game_record.winner = player_str[1 - player]
            break

        is_repetition, is_check_repetition = position.is_repetition()
        if is_repetition:
            if is_check_repetition:
                game_record.winner = player_str[player]
            else:
                game_record.winner = player_str[1]

            break

        # Think a next move.
        start_time = time.time()
        next_move = engines[player].ask_nextmove(position, timelimits, byoyomi)
        elapsed = int(1000 * (time.time() - start_time))

        if next_move == 'resign':
            game_record.winner = player_str[1 - player]
            break

        timelimits[player] -= elapsed
        game_record.sfen_kif = game_record.sfen_kif + next_move + " "

        # Detect legal moves.
        if not next_move in [m.sfen() for m in legal_moves]:
            game_record.winner = 1 - player
            break

        next_move = position.sfen_to_move(next_move)
        position.do_move(next_move)

    game_record.sfen_kif = game_record.sfen_kif.rstrip()
    game_record.timestamp = datetime.datetime.now().timestamp()
    game_record.ply = len(game_record.sfen_kif.split())

    return game_record

def main():
    with open('./settings.json') as f:
        settings = json.load(f)

    log_file = settings['config']['log_dir'] + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.json'

    # Start up engines.
    engines = [None for _ in range(2)]
    engines[0] = Engine(settings['engine1']['name'],
                        settings['engine1']['path'],
                        settings['engine1']['cwd'],
                        settings['engine1']['args'],
                        settings['engine1']['usi_option'])
    engines[1] = Engine(settings['engine2']['name'],
                        settings['engine2']['path'],
                        settings['engine2']['cwd'],
                        settings['engine2']['args'],
                        settings['engine2']['usi_option'])

    for engine in engines:
        engine.usi()

    result = {
        'engine1': engines[0].name,
        'engine2': engines[1].name,
        'records': [],
        'result': {}
    }

    # Engine1's perspective.
    win, lose, draw = 0, 0, 0

    for i in range(settings['config']['games']):
        if i % 2 == 0:
            game_record = conduct_game(engines, settings['config']['max_moves'], settings['config']['timelimit'], settings['config']['byoyomi'])
            game_record.first_player = 1
        else:
            game_record = conduct_game([engines[1], engines[0]], settings['config']['max_moves'], settings['config']['timelimit'], settings['config']['byoyomi'])
            game_record.first_player = 2

        result['records'].append(game_record.__dict__)

        if game_record.winner == 'DRAW':
            draw += 1
        else:
            if i % 2 == 0:
                if game_record.winner == 'SENTE':
                    win += 1
                else:
                    lose += 1
            else:
                if game_record.winner == 'GOTE':
                    win += 1
                else:
                    lose += 1

        result['result']['win'] = win
        result['result']['lose'] = lose
        result['result']['draw'] = draw

        # Output to the log file.
        with open(log_file, 'w') as f:
            f.write(json.dumps(result, indent=4))
            f.write('\n')

    for engine in engines:
        engine.quit()

if __name__ == '__main__':
    main()
