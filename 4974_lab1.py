import sys
import os
import enum
import socket
import struct

class TftpProcessor(object):

    """
    Implements logic for a TFTP server.
    The input to this object is a received UDP packet,
    the output is the packets to be written to the socket.
    This class MUST NOT know anything about the existing sockets
    its input and outputs are byte arrays ONLY.
    Store the output packets in a buffer (some list) in this class
    the function get_next_output_packet returns the first item in
    the packets to be sent.
    This class is also responsible for reading/writing files to the
    hard disk.
    Failing to comply with those requirements will invalidate
    your submission.
    Feel free to add more functions to this class as long as
    those functions don't interact with sockets nor inputs from
    user/sockets. For example, you can add functions that you
    think they are "private" only. Private functions in Python
    start with an "_", check the example below
    """

    class TftpPacketType(enum.Enum):
        """
        Represents a TFTP packet type add the missing types here and
        modify the existing values as necessary.
        """
        RRQ = 1
        WRQ = 2
        DATA = 3
        ACK = 4
        ERROR = 5

    class TftpErrorTypes(enum.Enum):

        fileNotFound = 1
        accessViolation = 2
        allocationExceeded = 3
        illegalTftpOperation = 4
        unknownPort = 5
        fileAlreadyExists = 6
        noSuchUser = 7

    def __init__(self):
        """
        Add and initialize the *internal* fields you need.
        Do NOT change the arguments passed to this function.
        Here's an example of what you can do inside this function.
        """
        self.packet_buffer = []
        self.fileBeingProcessed = ''
        pass

    def process_udp_packet(self, packet_data, packet_source):
        """
        Parse the input packet, execute your logic according to that packet.
        packet data is a bytearray, packet source contains the address
        information of the sender.
        """
        print(f"Received a packet from {packet_source}")
        parsedPacket = self._parse_udp_packet(packet_data)
        out_packet = self._constructUdpPacket(parsedPacket)
        if (out_packet is not None):
            self.packet_buffer.append(out_packet)

# ------------------------------------------------------------------------------------------------------------

    def get_next_output_packet(self):
        return self.packet_buffer.pop(0)

# ------------------------------------------------------------------------------------------------------------

    def has_pending_packets_to_be_sent(self):
        return len(self.packet_buffer) != 0

# ------------------------------------------------------------------------------------------------------------
    def _parse_udp_packet(self, packet_bytes):
        parsedPacket = []
        type = struct.unpack('!H', packet_bytes[:2])
        type = type[0]
        parsedPacket.append(type)
        currIndex = 2
        if type == self.TftpPacketType.WRQ.value or type == self.TftpPacketType.RRQ.value:
            parsedPacket = self._parseReadWriteRequest(packet_bytes, currIndex, parsedPacket)
        elif type == self.TftpPacketType.DATA.value:
            parsedPacket = self._parseDataPacket(packet_bytes, currIndex, parsedPacket)
        elif type == self.TftpPacketType.ACK.value:
            parsedPacket = self._parseACKPacket(packet_bytes, currIndex, parsedPacket)
        else:
            parsedPacket = self._parseErrorPacket(packet_bytes, currIndex, parsedPacket)
        return parsedPacket

# ------------------------------------------------------------------------------------------------------------

    def _constructUdpPacket(self, parsedPacket):

        outPutPacket = []
        currIndex = 0
        type = parsedPacket[currIndex]
        currIndex = currIndex + 1
        if type == self.TftpPacketType.RRQ.value: #send data
            out_pack = self._constructReadRespononse(currIndex, parsedPacket)
            return out_pack
        elif type == self.TftpPacketType.WRQ.value: #send ack
            pass
        elif type == self.TftpPacketType.ACK.value:# send data
            out_pack = self._constructACKResponse(currIndex, parsedPacket)
            return out_pack
            pass

# ------------------------------------------------------------------------------------------------------------
    def _constructReadRespononse(self, currIndex, parsedPacket):

        filename = parsedPacket[currIndex]
        currIndex = currIndex + 1
        mode = parsedPacket[currIndex]
        if self._checkFileAvailability(filename) and mode == 'octet':
            chunk = self._getReadFileDataChunck(0)
            packetContents = bytes(chr(0) + chr(self.TftpPacketType.DATA.value) + chr(0) + chr(1), 'utf8')
            packetContents = packetContents + chunk
            return packetContents
        else:
            packetContents = bytes(chr(0) + chr(self.TftpPacketType.ERROR.value) + chr(0) +chr(self.TftpErrorTypes.fileNotFound.value)+'FILENOTFOUND'+ chr(0), 'utf8')
            return packetContents
# ------------------------------------------------------------------------------------------------------------

    def _getReadFileDataChunck(self, blockNumber):

        file = open(self.fileBeingProcessed, 'rb')
        file.seek(blockNumber * 512)
        chunk = file.read(512)
        file.close()
        return chunk

# ------------------------------------------------------------------------------------------------------------
    def _constructACKResponse(self, currIndex, parsedPacket):

        blockNumber = parsedPacket[currIndex]
        chunk = self._getReadFileDataChunck(blockNumber)
        blockNumber = blockNumber + 1
        packetContents = bytes(chr(0) + chr(self.TftpPacketType.DATA.value) + chr(0) + chr(blockNumber), 'utf8')
        packetContents = packetContents + chunk
        print(list(packetContents))
        return packetContents



# ------------------------------------------------------------------------------------------------------------

    def _checkFileAvailability(self, filename):

        if os.path.isfile(filename):
            return True
        else:
            return False
# ------------------------------------------------------------------------------------------------------------

    def _parseReadWriteRequest(self, packet_bytes, currIndex, parsedPacket):
        nameLength = self._getStringLenght(packet_bytes, start=currIndex)
        filename = struct.unpack('!' + str(nameLength) + 's', packet_bytes[currIndex:currIndex + nameLength])
        filename = str(filename[0], 'utf8')
        self.fileBeingProcessed = filename
        parsedPacket.append(filename)
        currIndex = currIndex + nameLength + 1
        modeLength = self._getStringLenght(packet_bytes, start=currIndex)
        mode = struct.unpack('!' + str(modeLength) + 's', packet_bytes[currIndex:currIndex + modeLength])
        mode = str(mode[0], 'utf8')
        parsedPacket.append(mode)
        return parsedPacket

# ------------------------------------------------------------------------------------------------------------
    def _parseDataPacket(self, packet_bytes, currIndex, parsedPacket):
        blockNumber = struct.unpack("!H", packet_bytes[currIndex: currIndex + 2])
        blockNumber = blockNumber[0]
        parsedPacket.append(blockNumber)
        currIndex = currIndex + 2
        print("Data packet Header info ends at {0} and contains{1}".format(currIndex, packet_bytes[currIndex]))
        if self._isNotLastDataPacket(packet_bytes):
            data = struct.unpack('512s', packet_bytes[currIndex: len(packet_bytes) - 1])
            data = str(data[0], 'utf8')
            parsedPacket.append(data)

        else:
            lastIndex = len(packet_bytes) - 5
            data = struct.unpack('i' + lastIndex + 's', packet_bytes[currIndex: len(packet_bytes) - 1])
            data = str(data[0], 'utf8')
            parsedPacket.append(data)

        return parsedPacket

# ------------------------------------------------------------------------------------------------------------
    def _parseACKPacket(self, packet_bytes, currIndex, parsedPacket):
        blockNumber = struct.unpack("!H", packet_bytes[currIndex: currIndex + 2])
        blockNumber = blockNumber[0]
        parsedPacket.append(blockNumber)
        print(parsedPacket)
        return parsedPacket

# ------------------------------------------------------------------------------------------------------------
    def _parseErrorPacket(self, packet_bytes, currIndex, parsedPacket):
        errorCode = struct.unpack("!H", packet_bytes[currIndex: currIndex + 2])
        errorCode = errorCode[0]
        parsedPacket.append(errorCode)
        currIndex = currIndex + 2
        errorLength = self._getStringLenght(packet_bytes, start=currIndex)
        errorName = struct.unpack('!' + str(errorLength) + 's', packet_bytes[currIndex:currIndex + errorLength])
        errorName = str(errorName[0], 'utf8')
        parsedPacket.append(errorName)
        return parsedPacket

# ------------------------------------------------------------------------------------------------------------

    def _getStringLenght(self, packetBytes, start):
        counter = 0
        for i in range(start, len(packetBytes) - 1):
            if packetBytes[i] != 0:
                counter = counter + 1
            else:
                break
        return counter

# ------------------------------------------------------------------------------------------------------------

    def _stringToTuple(self,tup):

        str = ''.join(tup)
        return str

# ------------------------------------------------------------------------------------------------------------
    def _isNotLastDataPacket(self, packet_bytes):
        if len(packet_bytes) < 516:
            return False
        else:
            return True
#------------------------------------------------------------------------------------------------------------




def check_file_name():
    script_name = os.path.basename(__file__)
    import re
    matches = re.findall(r"(\d{4}_)+lab1\.(py|rar|zip)", script_name)
    if not matches:
        print(f"[WARN] File name is invalid [{script_name}]")
    pass


def setup_sockets(address):
    """
    Socket logic MUST NOT be written in the TftpProcessor
    class. It knows nothing about the sockets.
    Feel free to delete this function.
    """
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverAdress = (address, 69)
    serverSocket.bind(serverAdress)
    do_socket_logic(serverSocket)
    # don't forget, the server's port is 69 (might require using sudo on Linux)
    print(f"TFTP server started on on [{address}]...")
    pass


def do_socket_logic(serverSocket):
    """
    Example function for some helper logic, in case you
    want to be tidy and avoid stuffing the main function.
    Feel free to delete this function.
    """
    proc = TftpProcessor()
    while 1:
        receivedPacket = serverSocket.recvfrom(2048)
        if receivedPacket:
            packetData, sender = receivedPacket
            proc.process_udp_packet(packetData, sender)
            if proc.has_pending_packets_to_be_sent():
                data = proc.get_next_output_packet()
                print("Data Retrieved")
                serverSocket.sendto(data, sender)

    pass


def get_arg(param_index, default=None):
    """
        Gets a command line argument by index (note: index starts from 1)
        If the argument is not supplies, it tries to use a default value.
        If a default value isn't supplied, an error message is printed
        and terminates the program.
    """
    try:
        return sys.argv[param_index]
    except IndexError as e:
        if default:
            return default
        else:
            print(e)
            print(f"[FATAL] The comamnd-line argument #[{param_index}] is missing")
            exit(-1)    # Program execution failed.


def main():
    """
     Write your code above this function.
    if you need the command line arguments
    """
    print("*" * 50)
    print("[LOG] Printing command line arguments\n", ",".join(sys.argv))
    check_file_name()
    print("*" * 50)

    # This argument is required.
    # For a server, this means the IP that the server socket
    # will use.
    # The IP of the server.
    ip_address = get_arg(1, "127.0.0.1")
    setup_sockets(ip_address)


if __name__ == "__main__":
    main()
