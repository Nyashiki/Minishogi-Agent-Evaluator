import minishogilib
import queue
import subprocess

class Engine():
    def __init__(self, name=None, path=None, cwd=None, args={}, usi_option={}):
        self.name = name
        self.usi_option = usi_option

        command = path
        for (key, value) in args.items():
            command = '{} {} {}'.format(command, key, value)

        self.process = subprocess.Popen(command.split(), cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.message_queue = queue.Queue()
        threading.Thread(target=self._message_reader).start()

    def _message_reader(verbose=False):
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
        message = queue.get()
        return message

    def ask_nextmove(self, position, timelimits, byoyomi):
        sfen_position = 'position sfen ' + ' '.join(position.sfen_kif(True))
        command = 'go btime {} wtime {} byoyomi'.format(timelimits[0], timelimits[1], byoyomi)

        self.send_message(sfen_position)
        self.send_message(command)

    def usi():
        self.send_message('usi')

        while True:
            line = self.readline()

            if line == 'usiok':
                break

    def isready():
        self.send_message('isready')

        while True:
            line = self.readline()

            if line == 'readyok':
                break

    def usinewgame():
        self.send_message('usinewgame')



class GameRecord():
    self.engine1_name = None
    self.engine2_name = None

    self.sfen_kif = []
    self.winner = 2  # 0 is engine1 win, 1 is engine2 win, and 2 is draw.

    self.timestamp = 0


def conduct_game(engines, max_move=512):
    assert len(engines) == 2, "len(engines) should be 2."

    # Start up engines.


    game_record = GameRecord
    position = minishogilib.Position()
    position.set_start_position()

    # Let's start a game!
    for ply in range(max_move):
        pass


def main():
    pass

if __name__ == '__main__':
    main()
