import sys
import os
import enum
import socket
import struct

class TftpProcessor(object):


    class TftpPacketType(enum.Enum):

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

        self.packet_buffer = []
        self.fileBeingProcessed = ''
        pass

    def process_udp_packet(self, packet_data, packet_source):

        print(f"Received a packet from {packet_source}")
        parsedPacket = self._parse_udp_packet(packet_data)
        out_packet = self._constructUdpPacket(parsedPacket)
        if (out_packet is not None):
            self.packet_buffer.append(out_packet)



    def get_next_output_packet(self):
        return self.packet_buffer.pop(0)



    def has_pending_packets_to_be_sent(self):
        return len(self.packet_buffer) != 0


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
        print(parsedPacket)
        return parsedPacket




    def _constructUdpPacket(self, parsedPacket):

        currIndex = 0
        type = parsedPacket[currIndex]
        currIndex = currIndex + 1
        if type == self.TftpPacketType.RRQ.value: #send data
            out_pack = self._constructReadRespononse(currIndex, parsedPacket)
            return out_pack
        elif type == self.TftpPacketType.WRQ.value: #send ack
            out_pack = self._constructWriteResponse(currIndex,parsedPacket)
            return out_pack
        elif type == self.TftpPacketType.ACK.value:# send data
            out_pack = self._constructACKResponse(currIndex, parsedPacket)
            return out_pack
        elif type == self.TftpPacketType.DATA.value: #send ACK
            out_pack = self._constructDataResponse(currIndex, parsedPacket)
            return  out_pack
        elif type == self.TftpPacketType.ERROR.value:
            out_pack = self._constructErrorResponse(currIndex, parsedPacket)
            return out_pack
        else:
            print("ERROR {0} Illegal TFTP Operation".format(self.TftpErrorTypes.illegalTftpOperation.value))



    def _constructReadRespononse(self, currIndex, parsedPacket):

        currIndex = currIndex + 1
        mode = parsedPacket[currIndex]
        if self._checkFileAvailability(self.fileBeingProcessed) and mode == 'octet':
            chunk = self._getReadFileDataChunck(0)
            packetContents = bytes(chr(0) + chr(self.TftpPacketType.DATA.value) + chr(0) + chr(1), 'ascii')
            packetContents = packetContents + chunk
            return packetContents
        else:
            packetContents = bytes(chr(0) + chr(self.TftpPacketType.ERROR.value) + chr(0) + chr(self.TftpErrorTypes.fileNotFound.value)+'FILENOTFOUND'+ chr(0), 'ascii')
            return packetContents


    def _constructACKResponse(self, currIndex, parsedPacket):

        blockNumber = parsedPacket[currIndex]
        chunk = self._getReadFileDataChunck(blockNumber)
        blockNumber = blockNumber + 1
        blockNumberBytes = blockNumber.to_bytes(2,"big")
        packetContents = bytes(chr(0) + chr(self.TftpPacketType.DATA.value), 'ascii')
        packetContents = packetContents + blockNumberBytes
        packetContents = packetContents + chunk
        return packetContents


    def _constructDataResponse(self,currIndex, parsedPacket):

        blockNumber = parsedPacket[currIndex]
        currIndex = currIndex + 1
        data = parsedPacket[currIndex]
        self._writeToFile(blockNumber, data)
        blockNumberBytes = blockNumber.to_bytes(2,"big")
        packetContents = bytes(chr(0) + chr(self.TftpPacketType.ACK.value), 'ascii')
        packetContents = packetContents + blockNumberBytes
        return packetContents

    def _constructWriteResponse(self, currIndex, parsedPacket):

        currIndex = currIndex + 1
        mode = parsedPacket[currIndex]
        flag = False
        if mode != 'octet':
            print("Mode is not octet, mode must be octet")
            return
        if self._checkFileAvailability(self.fileBeingProcessed) and mode == 'octet':
            y = input("File Already Exists press y to overwrite\n")
            if y == 'y' or y == "Y":
                flag = True
            else:
                packetContents = bytes(chr(0) + chr(self.TftpPacketType.ERROR.value) + chr(0) + chr(self.TftpErrorTypes.fileAlreadyExists.value) + 'FileAlreadyExists' + chr(0), 'ascii')
                print("File Already Exists and Cannot be overwritten")
                return packetContents
        if (not(self._checkFileAvailability(self.fileBeingProcessed)) and mode == 'octet') or flag:
            packetContents = bytes(chr(0) + chr(4) + chr(0) + chr(0), 'ascii')
            return packetContents


    def _constructErrorResponse(self, currIndex, parsedPacket):
        errorCode = parsedPacket[currIndex]
        currIndex = currIndex + 1
        errorMessage = parsedPacket[currIndex]
        print(f"Error Occured ErrorCode {0}.\nError message: {1}".format(errorCode, errorMessage))
        return None



    def _getReadFileDataChunck(self, blockNumber):

        file = open(self.fileBeingProcessed, 'rb')
        file.seek(blockNumber * 512)
        chunk = file.read(512)
        file.close()
        return chunk

    def _writeToFile(self, blockNumber, data):
        file = open(self.fileBeingProcessed, 'ab')
        file.seek((blockNumber - 1) * 512)
        data = bytes(data, 'ascii')
        file.write(data)
        file.close()
        return


    def _checkFileAvailability(self, filename):

        if os.path.isfile(filename):
            return True
        else:
            return False


    def _parseReadWriteRequest(self, packet_bytes, currIndex, parsedPacket):
        nameLength = self._getStringLenght(packet_bytes, start=currIndex)
        filename = struct.unpack('!' + str(nameLength) + 's', packet_bytes[currIndex:currIndex + nameLength])
        filename = str(filename[0], 'ascii')
        self.fileBeingProcessed = filename
        parsedPacket.append(filename)
        currIndex = currIndex + nameLength + 1
        modeLength = self._getStringLenght(packet_bytes, start=currIndex)
        mode = struct.unpack('!' + str(modeLength) + 's', packet_bytes[currIndex:currIndex + modeLength])
        mode = str(mode[0], 'ascii')
        parsedPacket.append(mode)
        return parsedPacket


    def _parseDataPacket(self, packet_bytes, currIndex, parsedPacket):
        blockNumber = struct.unpack("!H", packet_bytes[currIndex: currIndex + 2])
        blockNumber = blockNumber[0]
        parsedPacket.append(blockNumber)
        currIndex = currIndex + 2
        if self._isNotLastDataPacket(packet_bytes):
            data = struct.unpack('512s', packet_bytes[currIndex: len(packet_bytes)])
            data = str(data[0], 'ascii')
            parsedPacket.append(data)

        else:
            lastIndex = len(packet_bytes) - 4
            data = struct.unpack(str(lastIndex) + 's', packet_bytes[currIndex: len(packet_bytes)])
            data = str(data[0], 'ascii')
            parsedPacket.append(data)

        return parsedPacket


    def _parseACKPacket(self, packet_bytes, currIndex, parsedPacket):
        blockNumber = struct.unpack("!H", packet_bytes[currIndex: currIndex + 2])
        blockNumber = blockNumber[0]
        parsedPacket.append(blockNumber)
        return parsedPacket


    def _parseErrorPacket(self, packet_bytes, currIndex, parsedPacket):
        errorCode = struct.unpack("!H", packet_bytes[currIndex: currIndex + 2])
        errorCode = errorCode[0]
        parsedPacket.append(errorCode)
        currIndex = currIndex + 2
        errorLength = self._getStringLenght(packet_bytes, start=currIndex)
        errorName = struct.unpack('!' + str(errorLength) + 's', packet_bytes[currIndex:currIndex + errorLength])
        errorName = str(errorName[0], 'ascii')
        parsedPacket.append(errorName)
        return parsedPacket



    def _getStringLenght(self, packetBytes, start):
        counter = 0
        for i in range(start, len(packetBytes) - 1):
            if packetBytes[i] != 0:
                counter = counter + 1
            else:
                break
        return counter



    def _stringToTuple(self,tup):

        str = ''.join(tup)
        return str


    def _isNotLastDataPacket(self, packet_bytes):
        if len(packet_bytes) < 516:
            return False
        else:
            return True





def setup_sockets(address):

    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverAdress = (address, 69)
    serverSocket.bind(serverAdress)
    startServer(serverSocket)
    # don't forget, the server's port is 69 (might require using sudo on Linux)
    print(f"TFTP server started on on [{address}]...")
    pass


def startServer(serverSocket):
    proc = TftpProcessor()
    while 1:
        receivedPacket = serverSocket.recvfrom(2048)
        if receivedPacket:
            packetData, sender = receivedPacket
            proc.process_udp_packet(packetData, sender)
            if proc.has_pending_packets_to_be_sent():
                data = proc.get_next_output_packet()
                serverSocket.sendto(data, sender)


def get_arg(param_index, default=None):

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

    print("*" * 50)
    print("[LOG] Printing command line arguments\n", ",".join(sys.argv))

    print("*" * 50)

    # This argument is required.
    # For a server, this means the IP that the server socket
    # will use.
    # The IP of the server.
    ip_address = get_arg(1, "127.0.0.1")
    setup_sockets(ip_address)


if __name__ == "__main__":
    main()
